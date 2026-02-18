# AI Voice Bot: Technical Report

A Real-Time Conversational Voice Agent Using Twilio, Google Cloud Speech Services, and Gemini LLM

---

## Table of Contents

1. [Abstract](#1-abstract)
2. [Introduction](#2-introduction)
3. [System Architecture](#3-system-architecture)
4. [Component Design](#4-component-design)
5. [Implementation Details](#5-implementation-details)
6. [Tool Calling and Function Execution](#6-tool-calling-and-function-execution)
7. [Data Persistence and Metrics](#7-data-persistence-and-metrics)
8. [Testing Strategy](#8-testing-strategy)
9. [Technology Stack](#9-technology-stack)
10. [Performance Considerations](#10-performance-considerations)
11. [Limitations and Future Work](#11-limitations-and-future-work)
12. [Conclusion](#12-conclusion)
13. [References](#13-references)
14. [Appendices](#14-appendices)

---

## 1. Abstract

This report presents the design and implementation of a real-time AI-powered voice bot capable of handling inbound phone calls. The system integrates Twilio for telephony, Google Cloud Speech-to-Text for real-time transcription, Google Gemini 2.0 Flash for conversational AI with function calling, and Google Cloud Text-to-Speech for audio response generation. The architecture uses a FastAPI backend with WebSocket streaming to achieve low-latency bidirectional audio communication. The bot supports multi-turn conversations, automated tool execution (order status checks, appointment booking), and comprehensive logging of call data and latency metrics. All components are designed for graceful degradation -- failures in any single service do not crash the call.

---

## 2. Introduction

### 2.1 Problem Statement

Traditional Interactive Voice Response (IVR) systems rely on rigid menu trees ("Press 1 for billing, press 2 for support") that frustrate callers and fail to handle natural language queries. Building a voice agent that can understand free-form speech, reason about the request, take actions (query databases, book appointments), and respond naturally in real time presents significant engineering challenges across multiple domains: telephony, speech processing, natural language understanding, and audio streaming.

### 2.2 Objectives

1. Build a fully functional voice bot that handles real phone calls end-to-end
2. Use streaming speech-to-text for low-latency transcription
3. Leverage a large language model (Gemini) for natural conversation and tool calling
4. Generate natural-sounding audio responses in the correct telephony format
5. Log all interactions and performance metrics to a database
6. Ensure the system degrades gracefully when individual components fail

### 2.3 Scope

The bot handles three business operations: checking order status, booking appointments, and answering frequently asked questions. The architecture is extensible to any number of tools by adding handler methods and Gemini function definitions.

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
+----------+       PSTN        +---------+     WebSocket      +----------+
|  Caller  | <--------------> | Twilio  | <-----------------> | FastAPI  |
|  (Phone) |    Voice Call     | Cloud   |   MULAW 8kHz Audio  | Server   |
+----------+                   +---------+                     +----------+
                                                                    |
                                                          +---------+---------+
                                                          |                   |
                                                   +------+------+    +-------+-------+
                                                   | Google STT  |    | Google TTS    |
                                                   | (Streaming) |    | (MULAW 8kHz)  |
                                                   +------+------+    +-------+-------+
                                                          |                   |
                                                          v                   ^
                                                   +------+------+           |
                                                   |   Gemini    +-----------+
                                                   |  2.0 Flash  |  Response Text
                                                   +------+------+
                                                          |
                                                   +------+------+
                                                   |  Business   |
                                                   |  Handlers   |
                                                   +------+------+
                                                          |
                                                   +------+------+
                                                   |  Database   |
                                                   |  (SQLite/   |
                                                   |  PostgreSQL) |
                                                   +-------------+
```

### 3.2 Data Flow

The system operates as a pipeline with the following stages:

| Stage | Component | Input | Output | Protocol |
|-------|-----------|-------|--------|----------|
| 1 | Twilio | Phone call (PSTN) | MULAW 8kHz audio | WebSocket |
| 2 | Google STT | MULAW 8kHz audio chunks | Text transcript | gRPC streaming |
| 3 | Gemini 2.0 Flash | Transcript + history | Text or function call | REST API |
| 4 | Business Handlers | Function name + args | Structured result | Local |
| 5 | Google TTS | Response text | MULAW 8kHz audio | REST API |
| 6 | Twilio | Base64 audio chunks | Voice audio to caller | WebSocket |

### 3.3 Concurrency Model

The system uses Python's `asyncio` event loop for all I/O-bound operations. Synchronous Google Cloud API calls are executed via `asyncio.to_thread()` to avoid blocking the event loop. The STT streaming recognition runs in a dedicated daemon thread that bridges audio from an asyncio queue using `run_coroutine_threadsafe()`.

---

## 4. Component Design

### 4.1 Telephony Layer (`src/telephony/`)

**Twilio Handler** generates TwiML XML responses that instruct Twilio to:
1. Play a greeting message using `<Say>`
2. Open a bidirectional WebSocket media stream using `<Connect><Stream>`

**Audio Stream Handler** processes Twilio media stream events over WebSocket:
- `connected` -- WebSocket established
- `start` -- Stream metadata (codec, sample rate)
- `media` -- Base64-encoded MULAW audio payload
- `stop` -- Call ended

**Call Manager** maintains a registry of active `ConversationOrchestrator` instances keyed by `call_sid`, with automatic cleanup on call end.

### 4.2 Speech-to-Text (`src/speech/google_stt.py`)

The STT module uses Google Cloud Speech-to-Text's streaming recognition API:

- **Background Thread:** A daemon thread runs `streaming_recognize()` continuously
- **Audio Bridge:** Audio chunks from the async WebSocket handler are placed in an `asyncio.Queue` and consumed by the sync thread via `run_coroutine_threadsafe()`
- **Transcript Filtering:** Only `is_final` transcripts are forwarded; interim results are discarded to avoid duplicate processing
- **Configuration:** MULAW encoding at 8000 Hz, `single_utterance=False` for continuous recognition
- **Error Recovery:** The recognition loop restarts automatically on stream errors

### 4.3 Text-to-Speech (`src/speech/google_tts.py`)

The TTS module uses Google Cloud Text-to-Speech with:

- **MULAW Encoding at 8kHz:** Audio is synthesized directly in Twilio's native format, eliminating the need for format conversion
- **Async Wrapping:** The synchronous `synthesize_speech()` call runs in a thread pool via `asyncio.to_thread()`
- **Client Reuse:** A single `TextToSpeechClient` instance is created at initialization and reused for all requests
- **Graceful Degradation:** Returns empty bytes on any error

### 4.4 Conversation AI (`src/ai/gemini_client.py`)

The Gemini client provides:

- **Structured Responses:** The `GeminiResponse` dataclass distinguishes between text responses and function calls with a single type
- **Function Calling:** Gemini can request tool execution; the client parses `function_call` from response parts
- **Function Results:** The `send_function_result()` method sends tool execution results back to Gemini as `FunctionResponse` protobuf parts, allowing Gemini to formulate a natural language response based on the data

### 4.5 Conversation Orchestrator (`src/ai/conversation.py`)

The orchestrator is the central coordination point:

```
on_audio_chunk(audio)
    |
    v
STT.process_audio_chunk(audio)
    |
    v
STT.get_transcript() --> transcript available?
    |                          |
    No (return)               Yes
                               |
                               v
                    handle_user_input(transcript)
                               |
                               v
                    Gemini.generate_response()
                               |
                    +----------+----------+
                    |                     |
              Text Response        Function Call
                    |                     |
                    v                     v
              TTS + send           Execute tool
                                         |
                                         v
                                  Gemini.send_function_result()
                                         |
                                  (loop up to 3 rounds)
                                         |
                                         v
                                   TTS + send
```

Key design decisions:
- **Tool Loop Cap:** Maximum 3 consecutive function calls per user turn prevents infinite loops
- **Latency Tracking:** Each stage (LLM, TTS) is timed and recorded
- **Audio Chunking:** Large TTS responses are split into 3200-byte chunks for streaming
- **Fire-and-Forget Logging:** Database writes use `asyncio.create_task()` so they never delay the audio response

---

## 5. Implementation Details

### 5.1 Audio Format

All audio in the system uses **MULAW encoding at 8000 Hz (8-bit, mono)**. This is Twilio's native media stream format. By configuring both Google STT and Google TTS to use MULAW 8kHz directly, we eliminate all audio format conversion, reducing latency and complexity.

### 5.2 Conversation History

The `ConversationContext` class maintains a sliding window of the last 10 conversation turns (20 messages) using a `collections.deque`. History is converted to Gemini's format (`{"role": ..., "parts": [...]}`) before each API call.

### 5.3 System Prompt

The Gemini model receives a system prompt optimized for voice interactions:
- Short responses (1-2 sentences)
- Natural phone conversation style
- One question at a time
- No special characters or formatting
- Numbers spelled out as words

### 5.4 Error Handling Strategy

Every external service call is wrapped in try/except:

| Component | On Failure | Fallback |
|-----------|-----------|----------|
| STT client creation | Log error | Stream not started; transcripts never produced |
| STT stream error | Log + restart loop | Automatic reconnection |
| Gemini API call | Log error | "I'm having trouble processing that. Could you repeat?" |
| TTS synthesis | Log error | Empty audio bytes (silent) |
| Database write | Log error | Call continues unaffected |
| Tool execution | Log error | Error result sent to Gemini |

---

## 6. Tool Calling and Function Execution

### 6.1 Tool Definitions

Tools are defined as JSON schemas in `src/business/tools.py` and passed to the Gemini model at initialization:

| Tool | Parameters | Description |
|------|-----------|-------------|
| `check_order_status` | `order_number` (string) | Look up order shipping status |
| `book_appointment` | `date` (string), `time` (string) | Schedule an appointment |

### 6.2 Dispatch Mechanism

When Gemini returns a `function_call` in its response:

1. The orchestrator looks up the tool name in `TOOL_METHOD_MAP`
2. Dispatches to the corresponding `BusinessHandlers` method with the provided arguments
3. Sends the structured result back to Gemini via `send_function_result()`
4. Gemini formulates a natural language response incorporating the tool result
5. If Gemini requests another tool call, the loop continues (up to 3 rounds)

### 6.3 Example Flow

**User:** "What's the status of order 12345?"

| Step | Actor | Action |
|------|-------|--------|
| 1 | STT | Transcribes: "what's the status of order twelve three four five" |
| 2 | Gemini | Returns `function_call: check_order_status(order_number="12345")` |
| 3 | Handler | Returns `{"status": "shipped", "tracking": "1Z999..."}` |
| 4 | Gemini | Returns text: "Order twelve three four five has shipped and is on the way." |
| 5 | TTS | Synthesizes audio from the response text |
| 6 | WebSocket | Streams audio back to Twilio |

---

## 7. Data Persistence and Metrics

### 7.1 Database Schema

Three tables track call data:

**calls** -- One row per phone call:

| Column | Type | Description |
|--------|------|-------------|
| call_sid | String (unique) | Twilio call identifier |
| start_time | DateTime | When the call started |
| end_time | DateTime | When the call ended |
| duration | Integer | Call length in seconds |
| status | String | "active" or "completed" |

**conversations** -- One row per message:

| Column | Type | Description |
|--------|------|-------------|
| call_sid | String (indexed) | Links to the call |
| role | String | "user" or "assistant" |
| message | Text | The spoken/generated text |
| intent | String (nullable) | Detected intent category |
| timestamp | DateTime | When the message occurred |

**call_metrics** -- One row per user turn:

| Column | Type | Description |
|--------|------|-------------|
| call_sid | String (indexed) | Links to the call |
| llm_latency | Integer | Gemini response time (ms) |
| tts_latency | Integer | TTS synthesis time (ms) |
| total_latency | Integer | End-to-end turn time (ms) |

### 7.2 Logging Architecture

Database writes are designed to never interfere with call processing:

1. Sync functions create and close their own database sessions
2. Async wrappers use `asyncio.to_thread()` to avoid blocking
3. Metrics logging uses `asyncio.create_task()` (fire-and-forget)
4. All errors are caught and logged -- a DB outage never drops a call

---

## 8. Testing Strategy

### 8.1 Test Coverage

| Test Suite | Tests | Coverage Area |
|------------|-------|---------------|
| `test_basic.py` | 1 | HTTP health endpoint |
| `test_call_flow.py` | 1 | TwiML response generation |
| `test_stt.py` | 7 | Transcript queue, audio buffering, timeout handling, client failure |
| `test_tts.py` | 6 | Audio synthesis, empty input, API errors, client initialization failure |
| `test_tool_dispatch.py` | 5 | Text response, single tool call, max rounds, unknown tool, tool errors |
| `test_call_logger.py` | 6 | Call lifecycle logging, message logging, metrics, async wrappers |
| **Total** | **26** | |

### 8.2 Testing Approach

**Unit Tests:** All external dependencies (Google Cloud clients, Gemini API) are mocked using `unittest.mock`. Tests validate internal logic without network calls.

**Database Tests:** Use in-memory SQLite (`sqlite:///:memory:`) with `monkeypatch` to replace the production session factory. This provides real SQL execution without file I/O.

**Integration Tests (tool dispatch):** The orchestrator is tested with mocked Gemini responses that simulate function calls, verifying the full dispatch loop including:
- Direct text responses (no tool call)
- Single tool call followed by text
- Maximum tool round enforcement (3 rounds)
- Unknown tool handling
- Tool execution errors

### 8.3 Testing Levels

| Level | Requirements | What It Tests |
|-------|-------------|---------------|
| Unit tests (`pytest`) | None | All logic with mocked services |
| Server smoke test (`curl`) | None | HTTP endpoints and TwiML generation |
| Gemini test (Python script) | Gemini API key | LLM responses and function calling |
| End-to-end voice test | All API keys + ngrok + phone | Complete call flow |

---

## 9. Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Web Framework | FastAPI | 0.109+ | HTTP + WebSocket server |
| ASGI Server | Uvicorn | 0.27+ | Production ASGI server |
| Telephony | Twilio | 8.11+ | Phone calls + media streams |
| Speech-to-Text | Google Cloud Speech | 2.24+ | Streaming transcription |
| Text-to-Speech | Google Cloud TTS | 2.16+ | Audio synthesis |
| LLM | Google Gemini 2.0 Flash | 0.3+ | Conversational AI + tool calling |
| ORM | SQLAlchemy | 2.0+ | Database abstraction |
| Database | SQLite / PostgreSQL | -- | Call and conversation storage |
| Settings | Pydantic Settings | 2.1+ | Environment configuration |
| Testing | pytest | 9.0+ | Test framework |
| Language | Python | 3.10+ | Runtime |

---

## 10. Performance Considerations

### 10.1 Latency Budget

For a natural conversation, total turn latency should be under 2 seconds:

| Stage | Typical Latency | Notes |
|-------|----------------|-------|
| STT (streaming) | 200-500ms | Continuous; transcript available shortly after speech ends |
| Gemini 2.0 Flash | 300-800ms | Optimized for speed; short response via system prompt |
| Tool execution | 1-10ms | Local mock handlers; real integrations will vary |
| TTS synthesis | 200-400ms | Single API call for short responses |
| WebSocket round-trip | 50-100ms | Depends on network |
| **Total** | **~750-1800ms** | Within conversational tolerance |

### 10.2 Optimization Techniques

1. **MULAW 8kHz everywhere:** No audio format conversion needed between components
2. **Streaming STT:** Transcription happens concurrently with speech, not after
3. **Short responses:** System prompt limits Gemini to 1-2 sentences (max 150 tokens)
4. **Audio chunking:** Large TTS responses are streamed in 3200-byte chunks rather than waiting for the full response
5. **Fire-and-forget logging:** Database writes don't block the audio pipeline
6. **Client reuse:** Google Cloud clients are created once per call, not per request

---

## 11. Limitations and Future Work

### 11.1 Current Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Google STT 5-minute streaming limit | Long calls may lose transcription | Restart loop with TODO for production |
| Single concurrent call per orchestrator | Each call gets its own instance | Call manager handles instance lifecycle |
| Mock business handlers | No real backend integrations | Easy to replace with real API calls |
| No barge-in support | Bot plays full response before listening | Would require STT + TTS coordination |
| No sentiment analysis | Missing caller emotion detection | Could add via Gemini prompt or separate model |

### 11.2 Future Enhancements

1. **STT Stream Restart:** Implement automatic reconnection for calls exceeding 5 minutes
2. **Barge-In:** Allow callers to interrupt the bot mid-response by detecting speech during TTS playback and canceling the audio stream
3. **Real Business Integrations:** Connect handlers to actual order management systems, CRM, and scheduling APIs
4. **Call Transfer:** Implement warm transfer to human agents using Twilio's `<Dial>` verb
5. **Multi-Language Support:** Configure STT/TTS language codes dynamically based on caller preference
6. **Caching:** Use Redis for frequently accessed data (FAQs, order status) to reduce API latency
7. **Monitoring Dashboard:** Build a real-time dashboard showing active calls, latency metrics, and conversation transcripts
8. **Load Testing:** Evaluate system behavior under concurrent call load

---

## 12. Conclusion

This project demonstrates a complete, functional voice bot architecture that bridges telephony with modern AI. The system successfully:

- Handles real phone calls with real-time audio streaming
- Transcribes speech using streaming recognition for low latency
- Uses Gemini's function calling to perform business operations mid-conversation
- Generates natural-sounding audio responses in the correct telephony format
- Logs all interactions and performance metrics to a database
- Degrades gracefully when any individual component fails

The modular architecture allows each component (STT, TTS, LLM, business logic) to be replaced or upgraded independently. The tool calling pattern is extensible to any number of business operations by adding handler methods and function definitions.

---

## 13. References

1. Twilio Media Streams Documentation. https://www.twilio.com/docs/voice/media-streams
2. Google Cloud Speech-to-Text Streaming. https://cloud.google.com/speech-to-text/docs/streaming-recognize
3. Google Cloud Text-to-Speech. https://cloud.google.com/text-to-speech/docs
4. Google Gemini API - Function Calling. https://ai.google.dev/gemini-api/docs/function-calling
5. FastAPI WebSocket Documentation. https://fastapi.tiangolo.com/advanced/websockets/
6. SQLAlchemy ORM Documentation. https://docs.sqlalchemy.org/en/20/
7. MULAW Audio Encoding (ITU-T G.711). https://www.itu.int/rec/T-REC-G.711

---

## 14. Appendices

### Appendix A: Project File Summary

| File | Lines | Purpose |
|------|-------|---------|
| `config/settings.py` | ~45 | Environment configuration via Pydantic |
| `config/prompts.py` | ~27 | Gemini system prompt for voice interactions |
| `src/api/main.py` | ~20 | FastAPI app initialization and startup |
| `src/api/routes.py` | ~30 | HTTP and WebSocket route definitions |
| `src/telephony/twilio_handler.py` | ~15 | TwiML XML response generation |
| `src/telephony/audio_stream.py` | ~44 | WebSocket media stream message handler |
| `src/telephony/call_manager.py` | ~20 | Per-call conversation registry |
| `src/speech/google_stt.py` | ~110 | Streaming STT with background thread |
| `src/speech/google_tts.py` | ~60 | TTS synthesis with MULAW 8kHz output |
| `src/speech/audio_utils.py` | ~20 | Base64 audio encode/decode helpers |
| `src/ai/gemini_client.py` | ~100 | Gemini API wrapper with tool support |
| `src/ai/conversation.py` | ~155 | Conversation orchestrator (core loop) |
| `src/ai/context.py` | ~20 | Conversation history management |
| `src/business/handlers.py` | ~35 | Business logic (order, appointment, FAQ) |
| `src/business/tools.py` | ~30 | Gemini function calling definitions |
| `src/database/models.py` | ~45 | SQLAlchemy models (Call, Conversation, Metrics) |
| `src/database/db.py` | ~25 | Database engine and session management |
| `src/database/call_logger.py` | ~100 | Async DB logging helpers |
| `src/utils/logger.py` | ~15 | Logging configuration |
| `src/utils/helpers.py` | ~30 | Retry decorator and byte chunking |

### Appendix B: Environment Variables

```env
# Twilio (required for phone calls)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+1234567890
PUBLIC_BASE_URL=https://your-url.ngrok.io

# Google Cloud (required for STT/TTS)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_PROJECT_ID=your-project-id

# Gemini (required for AI)
GEMINI_API_KEY=AIzaSy...

# Application
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///./voice_bot.db
HOST=0.0.0.0
PORT=8000
```

### Appendix C: API Endpoint Specifications

**GET /** -- Health Check
```json
Response 200: {"status": "ok", "message": "AI Voice Bot is running"}
```

**POST /voice** -- Twilio Voice Webhook
```xml
Response 200:
<Response>
  <Say>Connecting you to our AI assistant. Please hold a moment.</Say>
  <Connect>
    <Stream url="wss://your-url/ws/audio-stream" />
  </Connect>
</Response>
```

**WS /ws/audio-stream/{call_sid}** -- Media Stream

Incoming events from Twilio:
```json
{"event": "connected", ...}
{"event": "start", "start": {"streamSid": "...", ...}}
{"event": "media", "media": {"payload": "<base64 MULAW audio>"}}
{"event": "stop", ...}
```

Outgoing events to Twilio:
```json
{"event": "media", "streamSid": "...", "media": {"payload": "<base64 MULAW audio>"}}
```

### Appendix D: Test Results

```
tests/test_basic.py::test_health_root                              PASSED
tests/test_call_flow.py::test_voice_webhook_returns_twiml          PASSED
tests/test_call_logger.py::test_log_call_start                     PASSED
tests/test_call_logger.py::test_log_call_end                       PASSED
tests/test_call_logger.py::test_log_call_end_missing_call          PASSED
tests/test_call_logger.py::test_log_message                        PASSED
tests/test_call_logger.py::test_log_metrics                        PASSED
tests/test_call_logger.py::test_async_wrappers_delegate_to_sync   PASSED
tests/test_stt.py::test_get_transcript_returns_none_when_empty     PASSED
tests/test_stt.py::test_get_transcript_returns_queued_item         PASSED
tests/test_stt.py::test_get_transcript_with_timeout                PASSED
tests/test_stt.py::test_get_transcript_timeout_returns_none        PASSED
tests/test_stt.py::test_process_audio_chunk_queues_data            PASSED
tests/test_stt.py::test_close_sets_running_false                   PASSED
tests/test_stt.py::test_client_creation_failure                    PASSED
tests/test_tool_dispatch.py::test_text_response_no_tool_call       PASSED
tests/test_tool_dispatch.py::test_single_tool_call_then_text       PASSED
tests/test_tool_dispatch.py::test_max_tool_rounds_respected        PASSED
tests/test_tool_dispatch.py::test_unknown_tool_returns_error       PASSED
tests/test_tool_dispatch.py::test_tool_execution_error_handled     PASSED
tests/test_tts.py::test_synthesize_returns_audio_bytes             PASSED
tests/test_tts.py::test_synthesize_empty_text_returns_empty        PASSED
tests/test_tts.py::test_synthesize_whitespace_returns_empty        PASSED
tests/test_tts.py::test_synthesize_handles_api_error               PASSED
tests/test_tts.py::test_audio_format                               PASSED
tests/test_tts.py::test_client_creation_failure                    PASSED

======================== 26 passed ========================
```
