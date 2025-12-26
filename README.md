# AI Voice Bot 🤖📞

An intelligent voice bot system that handles phone calls using AI, built with Twilio, Google Speech APIs, and Gemini LLM.

## Features

- 📞 Real-time phone call handling via Twilio
- �� Google Speech-to-Text for voice recognition
- 🔊 Google Text-to-Speech for natural responses
- 🤖 Gemini LLM for intelligent conversation
- ⚡ FastAPI backend with WebSocket support
- 🗄️ Database integration for call logging
- 🚀 Ready for deployment (Railway/Render)

## Tech Stack

- **Telephony**: Twilio Voice API
- **Speech**: Google Cloud Speech-to-Text & Text-to-Speech
- **AI**: Google Gemini LLM
- **Backend**: FastAPI + Python 3.11+
- **Database**: SQLAlchemy (PostgreSQL/SQLite)
- **Deployment**: Railway/Render compatible

## Project Structure
```
ai-voice-bot/
├── config/          # Configuration and prompts
├── src/
│   ├── telephony/   # Twilio integration
│   ├── speech/      # STT/TTS handling
│   ├── ai/          # Gemini LLM integration
│   ├── business/    # Business logic
│   ├── database/    # Database models
│   ├── utils/       # Utilities
│   └── api/         # FastAPI application
├── tests/           # Test suite
├── scripts/         # Setup & testing scripts
└── docs/            # Documentation
```

## Quick Start

### Prerequisites

- Python 3.11+
- Twilio account
- Google Cloud account (Speech & Gemini API enabled)

### Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/ai-voice-bot.git
cd ai-voice-bot
```

2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your API keys
```

5. Run the application
```bash
uvicorn src.api.main:app --reload
```

## Configuration

Create a `.env` file with:
```env
# Twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_twilio_number

# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
GOOGLE_PROJECT_ID=your_project_id

# Gemini
GEMINI_API_KEY=your_gemini_api_key

# Application
ENVIRONMENT=development
DATABASE_URL=sqlite:///./voice_bot.db
```

## Usage

### Making a Test Call
```bash
python scripts/test_call.py
```

### Setting Up Twilio Webhook
```bash
python scripts/setup_twilio.py
```

## API Endpoints

- `POST /webhook/voice` - Twilio voice webhook
- `WS /ws/call/{call_sid}` - WebSocket for audio streaming
- `GET /health` - Health check

## Deployment

See [docs/deployment.md](docs/deployment.md) for deployment instructions.

## Use Cases

- 📞 Customer service automation
- �� Appointment scheduling
- 🎯 Lead qualification
- 📢 Automated outreach campaigns
- ℹ️ Information hotlines

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with Twilio Voice API
- Powered by Google Gemini & Cloud Speech
- FastAPI framework
