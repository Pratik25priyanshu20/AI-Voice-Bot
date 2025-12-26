# AI Voice Bot

An intelligent, cost-optimized voice bot that answers calls with Twilio, transcribes with Google Speech-to-Text, thinks with Gemini, and replies with Google Text-to-Speech via a FastAPI backend.

## Features

- Real-time phone handling via Twilio Media Streams
- Google Speech-to-Text and Text-to-Speech integration
- Gemini-powered conversational responses with tool calling hooks
- FastAPI backend with WebSocket streaming
- SQLAlchemy models ready for Postgres/SQLite logging
- Deployment-ready for Railway/Render/Fly.io

## Project Structure
```
ai-voice-bot/
├── config/          # Settings and system prompts
├── src/
│   ├── telephony/   # Twilio webhooks and media streams
│   ├── speech/      # STT/TTS helpers
│   ├── ai/          # Gemini client and conversation loop
│   ├── business/    # Business logic + tool contracts
│   ├── database/    # SQLAlchemy models and session
│   ├── utils/       # Logging and helpers
│   └── api/         # FastAPI entrypoints
├── tests/           # Basic smoke tests
├── scripts/         # Twilio setup and call testing
└── docs/            # Setup and deployment notes
```

## Quick Start

### Prerequisites
- Python 3.10+
- Twilio account with a voice-enabled number
- Google Cloud project with Speech-to-Text, Text-to-Speech, and Gemini API enabled

### Install and run
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # fill in your keys
uvicorn src.api.main:app --reload --port 8000
```

Expose your local server to Twilio during development:
```bash
ngrok http 8000
```
Then point your Twilio number's voice webhook to `https://<ngrok-id>.ngrok.io/voice`.

## Environment Variables
See `.env.example` for all settings:
- Twilio: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
- Google: `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_PROJECT_ID`
- Gemini: `GEMINI_API_KEY`
- App: `ENVIRONMENT`, `DEBUG`, `LOG_LEVEL`, `DATABASE_URL`, `HOST`, `PORT`

## API Surface
- `POST /voice` — Twilio voice webhook (responds with TwiML to start media stream)
- `POST /status` — Twilio status callback placeholder
- `WS /ws/audio-stream/{call_sid}` — Media stream WebSocket endpoint
- `GET /` — Basic health check

## Deployment
Use the included `Procfile` for Railway/Render:
```
web: uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
```
Add your environment variables in the platform dashboard and update your Twilio webhook to the deployed URL.

## Testing
```bash
pytest
```

## Next Steps
- Wire real Google STT/TTS streaming in `src/speech/`
- Implement Gemini tool execution against real business systems
- Add persistence via `src/database/` and expand the test suite
