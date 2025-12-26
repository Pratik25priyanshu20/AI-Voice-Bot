# Local Setup Guide

## 1) Prerequisites
- Python 3.10+
- Twilio account with a voice-capable number
- Google Cloud project with Speech-to-Text, Text-to-Speech, and Gemini APIs enabled
- ngrok (for local webhook tunneling)

## 2) Install dependencies
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 3) Configure environment
```bash
cp .env.example .env
```
Fill in Twilio, Google, and Gemini values. Ensure `GOOGLE_APPLICATION_CREDENTIALS` points to your service account JSON path.

## 4) Run the API
```bash
uvicorn src.api.main:app --reload --port 8000
```

## 5) Expose locally to Twilio
```bash
ngrok http 8000
```
Update your Twilio phone number webhook to `https://<ngrok-id>.ngrok.io/voice`.

## 6) Try it
- Call your Twilio number; you should hear the placeholder greeting.
- Watch the server logs for incoming webhook and WebSocket events.

## Troubleshooting
- If Gemini is not configured, the bot responds with a fallback message.
- Verify your Twilio credentials and webhook URL if you do not see requests hitting `/voice`.
- For SSL issues, ensure you use the `https` ngrok URL for Twilio and `wss` for media streams.
