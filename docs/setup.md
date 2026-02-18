# Setup and Testing Guide

Complete step-by-step instructions to set up, run, and test the AI Voice Bot at every level.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Installation](#2-installation)
3. [Configuration](#3-configuration)
4. [Level 1: Unit Tests (No API Keys Needed)](#4-level-1-unit-tests-no-api-keys-needed)
5. [Level 2: Server Smoke Test (No API Keys Needed)](#5-level-2-server-smoke-test-no-api-keys-needed)
6. [Level 3: Gemini-Only Test (Gemini API Key Only)](#6-level-3-gemini-only-test-gemini-api-key-only)
7. [Level 4: Full End-to-End Voice Test (All Keys + Phone)](#7-level-4-full-end-to-end-voice-test-all-keys--phone)
8. [Understanding the Logs](#8-understanding-the-logs)
9. [Database Inspection](#9-database-inspection)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Prerequisites

### Software

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Runtime |
| pip | Latest | Package manager |
| ngrok | Any | Tunnel local server to internet (for Twilio) |
| Git | Any | Version control |

### Accounts and API Keys

| Service | What You Need | Free Tier? |
|---------|---------------|------------|
| **Twilio** | Account SID, Auth Token, Phone Number | Yes (trial) |
| **Google Cloud** | Service Account JSON with Speech-to-Text and Text-to-Speech APIs enabled | Yes ($300 credit) |
| **Google Gemini** | Gemini API Key (from Google AI Studio) | Yes (free tier) |

### Getting the API Keys

**Twilio:**
1. Sign up at [twilio.com](https://www.twilio.com/)
2. From the Console dashboard, copy your **Account SID** and **Auth Token**
3. Buy or claim a phone number with Voice capability
4. Note the phone number (e.g., `+1234567890`)

**Google Cloud (STT + TTS):**
1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
2. Create a new project (or use an existing one)
3. Enable these APIs:
   - Cloud Speech-to-Text API
   - Cloud Text-to-Speech API
4. Go to IAM & Admin > Service Accounts
5. Create a service account, grant it the "Editor" role
6. Generate a JSON key and download it
7. Save the JSON file somewhere safe (e.g., `~/keys/google-sa.json`)

**Gemini API Key:**
1. Go to [aistudio.google.com](https://aistudio.google.com/)
2. Click "Get API Key"
3. Create a key for your Google Cloud project
4. Copy the key

---

## 2. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd ai-voice-bot

# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate          # Windows

# Install dependencies
pip install -r requirements.txt

# Install test dependencies
pip install pytest httpx
```

Verify the install:

```bash
python -c "from src.api.main import app; print('OK')"
```

---

## 3. Configuration

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
PUBLIC_BASE_URL=https://your-ngrok-url.ngrok.io

# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/your/service-account.json
GOOGLE_PROJECT_ID=your-project-id

# Gemini
GEMINI_API_KEY=AIzaSy...your_key_here

# App (defaults are fine for development)
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///./voice_bot.db
```

**Important:** `GOOGLE_APPLICATION_CREDENTIALS` must be an absolute path to the JSON file.

---

## 4. Level 1: Unit Tests (No API Keys Needed)

This runs all 26 tests with mocked external services. No API keys, no internet, no phone required.

```bash
pytest tests/ -v
```

**Expected output:**

```
tests/test_basic.py::test_health_root                         PASSED
tests/test_call_flow.py::test_voice_webhook_returns_twiml     PASSED
tests/test_call_logger.py::test_log_call_start                PASSED
tests/test_call_logger.py::test_log_call_end                  PASSED
tests/test_call_logger.py::test_log_call_end_missing_call     PASSED
tests/test_call_logger.py::test_log_message                   PASSED
tests/test_call_logger.py::test_log_metrics                   PASSED
tests/test_call_logger.py::test_async_wrappers_delegate_to_sync PASSED
tests/test_stt.py::test_get_transcript_returns_none_when_empty PASSED
tests/test_stt.py::test_get_transcript_returns_queued_item    PASSED
tests/test_stt.py::test_get_transcript_with_timeout           PASSED
tests/test_stt.py::test_get_transcript_timeout_returns_none   PASSED
tests/test_stt.py::test_process_audio_chunk_queues_data       PASSED
tests/test_stt.py::test_close_sets_running_false              PASSED
tests/test_stt.py::test_client_creation_failure               PASSED
tests/test_tool_dispatch.py::test_text_response_no_tool_call  PASSED
tests/test_tool_dispatch.py::test_single_tool_call_then_text  PASSED
tests/test_tool_dispatch.py::test_max_tool_rounds_respected   PASSED
tests/test_tool_dispatch.py::test_unknown_tool_returns_error  PASSED
tests/test_tool_dispatch.py::test_tool_execution_error_handled PASSED
tests/test_tts.py::test_synthesize_returns_audio_bytes        PASSED
tests/test_tts.py::test_synthesize_empty_text_returns_empty   PASSED
tests/test_tts.py::test_synthesize_whitespace_returns_empty   PASSED
tests/test_tts.py::test_synthesize_handles_api_error          PASSED
tests/test_tts.py::test_audio_format                          PASSED
tests/test_tts.py::test_client_creation_failure               PASSED

======================== 26 passed ========================
```

**What each test file covers:**

| File | Tests | What It Validates |
|------|-------|-------------------|
| `test_basic.py` | 1 | Health endpoint returns 200 |
| `test_call_flow.py` | 1 | `/voice` returns valid TwiML with `<Stream>` |
| `test_stt.py` | 7 | Transcript queue, audio buffering, timeout, graceful client failure |
| `test_tts.py` | 6 | Audio synthesis, empty input handling, API errors, client failure |
| `test_tool_dispatch.py` | 5 | Text response, single tool call, max rounds cap, unknown tool, tool errors |
| `test_call_logger.py` | 6 | Call start/end, message logging, metrics, async delegation |

---

## 5. Level 2: Server Smoke Test (No API Keys Needed)

Start the server and verify the HTTP endpoints work:

```bash
# Terminal 1: Start server
uvicorn src.api.main:app --reload --port 8000
```

```bash
# Terminal 2: Test endpoints

# Health check
curl http://localhost:8000/
# Expected: {"status":"ok","message":"AI Voice Bot is running"}

# Voice webhook (what Twilio calls)
curl -X POST http://localhost:8000/voice
# Expected: XML containing <Response><Say>...</Say><Connect><Stream>...</Stream></Connect></Response>

# Status callback
curl -X POST http://localhost:8000/status
# Expected: {"status":"received"}
```

The voice endpoint returns TwiML XML -- this is what tells Twilio to open a WebSocket media stream to your server.

---

## 6. Level 3: Gemini-Only Test (Gemini API Key Only)

Test the AI brain without any telephony. You only need `GEMINI_API_KEY` in your `.env`.

```bash
python3 -c "
import asyncio
from src.ai.gemini_client import GeminiClient

async def test():
    client = GeminiClient()

    # Test 1: Simple text response
    resp = await client.generate_response([], 'Hi, how are you?')
    print(f'Test 1 - Text response:')
    print(f'  text: {resp.text}')
    print(f'  is_function_call: {resp.is_function_call}')
    print()

    # Test 2: Should trigger tool call
    resp = await client.generate_response([], 'Check the status of order 12345')
    print(f'Test 2 - Tool call:')
    print(f'  text: {resp.text}')
    print(f'  function_call: {resp.function_call}')
    print(f'  function_args: {resp.function_args}')
    print()

    # Test 3: Send function result back
    if resp.is_function_call:
        result = {'order_number': '12345', 'status': 'shipped', 'tracking': '1Z999AA10123456784'}
        resp2 = await client.send_function_result([], resp.function_call, result)
        print(f'Test 3 - After function result:')
        print(f'  text: {resp2.text}')
        print(f'  is_function_call: {resp2.is_function_call}')

asyncio.run(test())
"
```

**Expected behavior:**
- Test 1: Returns a greeting text, no function call
- Test 2: Returns `function_call="check_order_status"` with `function_args={"order_number": "12345"}`
- Test 3: Returns a natural language response about the order status

---

## 7. Level 4: Full End-to-End Voice Test (All Keys + Phone)

This is the complete test -- a real phone call to your bot.

### Step 1: Start the server

```bash
uvicorn src.api.main:app --port 8000
```

### Step 2: Start ngrok

```bash
ngrok http 8000
```

Note the HTTPS URL (e.g., `https://abc123.ngrok-free.app`).

### Step 3: Update your .env

```env
PUBLIC_BASE_URL=https://abc123.ngrok-free.app
```

Restart the server after changing `.env`.

### Step 4: Configure Twilio webhook

1. Go to [Twilio Console](https://console.twilio.com/) > Phone Numbers > Active Numbers
2. Click your number
3. Under "Voice Configuration":
   - Set "A call comes in" to **Webhook**
   - URL: `https://abc123.ngrok-free.app/voice`
   - Method: **HTTP POST**
4. Save

### Step 5: Make the call

1. Call your Twilio number from any phone
2. You should hear: **"Connecting you to our AI assistant. Please hold a moment."** (Twilio TwiML)
3. Then: **"Hello! How can I help you today?"** (bot's greeting via TTS)
4. Speak naturally -- try these:
   - "What's the status of order 12345?"
   - "I'd like to book an appointment for tomorrow at 3 PM"
   - "What are your business hours?"
   - "Can I return an item?"

### Step 6: Watch the logs

In your server terminal, you'll see:

```
INFO: Call CA... connected
INFO: Call CA... started
INFO: STT stream started at 8000 Hz
INFO: Synthesizing TTS for text: Hello! How can I help you today?
INFO: STT transcript: what's the status of my order twelve three four five
INFO: User said: what's the status of my order twelve three four five
INFO: Tool call 1: check_order_status({'order_number': '12345'})
INFO: Synthesizing TTS for text: Order twelve three four five has shipped...
INFO: Call CA... ended
INFO: STT stream closed
```

---

## 8. Understanding the Logs

The server logs show the complete call flow:

| Log Message | What It Means |
|-------------|---------------|
| `Call CA... connected` | Twilio WebSocket connected |
| `STT stream started` | Google Speech recognition thread launched |
| `STT transcript: ...` | Speech was recognized (final transcript) |
| `User said: ...` | Transcript sent to Gemini |
| `Tool call N: name(args)` | Gemini requested a function call |
| `Synthesizing TTS for text: ...` | Response being converted to audio |
| `Call CA... ended` | Call hung up, resources cleaned up |

---

## 9. Database Inspection

After calls, the SQLite database contains call records:

```bash
# Install sqlite3 if not available, then inspect
sqlite3 voice_bot.db

-- See all calls
SELECT * FROM calls;

-- See conversation messages
SELECT call_sid, role, message, timestamp FROM conversations ORDER BY timestamp;

-- See latency metrics
SELECT call_sid, llm_latency, tts_latency, total_latency FROM call_metrics;
```

Example output:

```
call_sid            | role      | message
CA123...            | user      | what's the status of my order twelve three four five
CA123...            | assistant | Order twelve three four five has shipped and is on the way.
```

---

## 10. Troubleshooting

### "GEMINI_API_KEY not configured"
- Check `.env` has `GEMINI_API_KEY=...` with no quotes around the value
- Restart the server after editing `.env`

### "Failed to create TTS/STT client"
- Check `GOOGLE_APPLICATION_CREDENTIALS` points to a valid JSON file
- Verify the file path is absolute (e.g., `/Users/you/keys/sa.json`, not `./sa.json`)
- Ensure Speech-to-Text and Text-to-Speech APIs are enabled in Google Cloud Console

### Twilio returns "Application error"
- Check the ngrok terminal for incoming requests
- Verify the webhook URL ends in `/voice`
- Make sure `PUBLIC_BASE_URL` in `.env` matches your ngrok URL exactly (no trailing slash)

### No audio / silence on the call
- Check server logs for errors
- Verify Google Cloud service account has proper permissions
- Ensure the ngrok URL uses `https://` (not `http://`)

### STT not recognizing speech
- Google STT has a ~5 minute streaming limit per session
- Short calls should work fine; long calls may need a server restart
- Check that audio is flowing (you should see `on_audio_chunk` activity in DEBUG logs)

### Database errors
- SQLite is used by default -- the file `voice_bot.db` is created automatically
- For PostgreSQL, set `DATABASE_URL=postgresql://user:pass@host:5432/dbname`
- DB failures are logged but never crash the call -- the bot continues working
