# AI Voice Bot

A real-time AI-powered voice bot that handles phone calls using Twilio Media Streams, Google Cloud Speech-to-Text, Google Gemini for conversational intelligence, and Google Cloud Text-to-Speech -- all orchestrated by a FastAPI backend with WebSocket audio streaming.

## How It Works

```
Caller --> Twilio --> WebSocket --> FastAPI
                                      |
                              Audio (MULAW 8kHz)
                                      |
                              Google STT (streaming)
                                      |
                                  Transcript
                                      |
                              Google Gemini 2.0 Flash
                              (+ function calling)
                                      |
                               Response Text
                                      |
                              Google TTS (MULAW 8kHz)
                                      |
                              Audio --> WebSocket --> Twilio --> Caller
```

1. A caller dials your Twilio number
2. Twilio hits `POST /voice`, gets TwiML that opens a WebSocket media stream
3. Raw MULAW 8kHz audio flows over WebSocket to the server
4. Google STT transcribes speech in real time (streaming recognition in a background thread)
5. Transcripts are sent to Gemini 2.0 Flash with conversation history
6. If Gemini requests a tool call (check order, book appointment), the bot executes it and sends results back to Gemini (up to 3 rounds)
7. Gemini's final text response is synthesized to MULAW 8kHz audio via Google TTS
8. Audio is chunked, base64-encoded, and streamed back through the WebSocket to Twilio
9. The caller hears the bot's response
10. All interactions are logged to the database with latency metrics

## Features

- **Real-time voice streaming** via Twilio Media Streams over WebSocket
- **Streaming speech-to-text** using Google Cloud Speech API with background thread
- **Gemini 2.0 Flash** for fast conversational responses with function calling
- **Tool calling loop** -- Gemini can call business functions (order status, appointments) and receive results before responding
- **Google Cloud TTS** with MULAW 8kHz output (native Twilio format, no conversion needed)
- **Per-call conversation state** with history management (max 10 turns)
- **Database logging** -- every call, message, and latency metric is recorded
- **Graceful degradation** -- missing API keys, failed services, or DB errors never crash a call
- **26 unit tests** covering STT, TTS, tool dispatch, and database logging

## Project Structure

```
ai-voice-bot/
├── config/
│   ├── settings.py          # Pydantic settings (env vars)
│   └── prompts.py           # Gemini system prompt
├── src/
│   ├── api/
│   │   ├── main.py          # FastAPI app, startup, DB init
│   │   └── routes.py        # HTTP + WebSocket endpoints
│   ├── telephony/
│   │   ├── twilio_handler.py    # TwiML response generation
│   │   ├── audio_stream.py      # WebSocket message handler
│   │   └── call_manager.py      # Per-call conversation registry
│   ├── speech/
│   │   ├── google_stt.py    # Streaming STT (background thread)
│   │   ├── google_tts.py    # TTS synthesis (MULAW 8kHz)
│   │   └── audio_utils.py   # Base64 encode/decode helpers
│   ├── ai/
│   │   ├── gemini_client.py # Gemini API + structured responses + function results
│   │   ├── conversation.py  # Orchestrator (STT -> LLM -> tool loop -> TTS -> WS)
│   │   └── context.py       # Conversation history (deque, max 10 turns)
│   ├── business/
│   │   ├── handlers.py      # Business logic (order status, appointments, FAQs)
│   │   └── tools.py         # Gemini function calling definitions
│   ├── database/
│   │   ├── models.py        # Call, Conversation, CallMetrics tables
│   │   ├── db.py            # SQLAlchemy engine + session
│   │   └── call_logger.py   # Async DB logging helpers
│   └── utils/
│       ├── logger.py        # Logging config
│       └── helpers.py       # retry_async, chunk_bytes
├── tests/
│   ├── test_basic.py        # Health check
│   ├── test_call_flow.py    # TwiML response
│   ├── test_stt.py          # STT unit tests (7 tests)
│   ├── test_tts.py          # TTS unit tests (6 tests)
│   ├── test_tool_dispatch.py    # Tool calling integration (5 tests)
│   └── test_call_logger.py      # DB logging tests (6 tests)
├── scripts/
│   ├── setup_twilio.py      # Twilio setup utility
│   └── test_call.py         # Manual call testing
├── docs/
│   ├── setup.md             # Step-by-step setup and testing guide
│   ├── deployment.md        # Deployment guide
│   └── report.md            # Technical report / paper
├── requirements.txt
├── .env.example
└── Procfile
```

## Quick Start

```bash
# 1. Clone and set up
git clone <your-repo-url>
cd ai-voice-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your API keys (see Environment Variables below)

# 3. Run tests
pytest tests/ -v

# 4. Start the server
uvicorn src.api.main:app --reload --port 8000

# 5. Expose to Twilio (separate terminal)
ngrok http 8000

# 6. Set Twilio webhook to https://<ngrok-id>.ngrok.io/voice
# 7. Call your Twilio number
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TWILIO_ACCOUNT_SID` | Yes | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Yes | Twilio Auth Token |
| `TWILIO_PHONE_NUMBER` | Yes | Your Twilio phone number |
| `PUBLIC_BASE_URL` | Yes | Public URL (ngrok or deployed) |
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | Path to Google Cloud service account JSON |
| `GOOGLE_PROJECT_ID` | No | Google Cloud project ID |
| `DATABASE_URL` | No | Database URL (default: `sqlite:///./voice_bot.db`) |
| `ENVIRONMENT` | No | `development` or `production` |
| `DEBUG` | No | Enable debug mode |
| `LOG_LEVEL` | No | Logging level (default: `INFO`) |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/voice` | Twilio voice webhook (returns TwiML with `<Stream>`) |
| `POST` | `/status` | Twilio status callback |
| `WS` | `/ws/audio-stream/{call_sid}` | WebSocket for Twilio media streams |

## Testing

```bash
# Run all 26 tests
pytest tests/ -v

# Run specific test files
pytest tests/test_tts.py -v
pytest tests/test_tool_dispatch.py -v
```

See [docs/setup.md](docs/setup.md) for detailed testing instructions at every level (unit, integration, end-to-end).

## Deployment

See [docs/deployment.md](docs/deployment.md) for Railway/Render/Fly.io instructions.

## Documentation

- [Setup and Testing Guide](docs/setup.md) -- step-by-step instructions
- [Deployment Guide](docs/deployment.md) -- production deployment
- [Technical Report](docs/report.md) -- architecture, design decisions, and evaluation (suitable for academic papers)
