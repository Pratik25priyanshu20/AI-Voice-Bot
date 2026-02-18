# Deployment Guide

How to deploy the AI Voice Bot to production on Railway, Render, or Fly.io.

---

## Prerequisites

Before deploying, make sure:

1. All 26 tests pass locally (`pytest tests/ -v`)
2. The app starts without errors (`uvicorn src.api.main:app`)
3. You have all API keys ready (Twilio, Google Cloud, Gemini)
4. Your code is pushed to a GitHub repository

---

## Option 1: Railway (Recommended)

Railway provides the simplest deployment with a free starter tier.

### Step 1: Push to GitHub

```bash
git add .
git commit -m "Deploy AI Voice Bot"
git push origin main
```

### Step 2: Create Railway Project

1. Go to [railway.app](https://railway.app/) and sign in with GitHub
2. Click "New Project" > "Deploy from GitHub repo"
3. Select your repository

### Step 3: Add Environment Variables

In the Railway dashboard, go to your service > Variables tab. Add:

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
GEMINI_API_KEY=your_gemini_key
GOOGLE_PROJECT_ID=your_project_id
ENVIRONMENT=production
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///./voice_bot.db
```

For `GOOGLE_APPLICATION_CREDENTIALS`, you have two options:
- **Option A:** Base64-encode your JSON key and decode it at startup (requires a small script)
- **Option B:** Use Google Cloud Workload Identity Federation (recommended for production)

### Step 4: Verify the Procfile

Railway auto-detects the `Procfile`:

```
web: uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### Step 5: Deploy

Railway builds and deploys automatically. Wait for the build to complete.

### Step 6: Get Your URL

Railway assigns a public URL like `https://your-app.up.railway.app`.

Set this in your environment variables:

```
PUBLIC_BASE_URL=https://your-app.up.railway.app
```

### Step 7: Configure Twilio

1. Go to [Twilio Console](https://console.twilio.com/) > Phone Numbers > Active Numbers
2. Click your number
3. Set Voice webhook to: `https://your-app.up.railway.app/voice` (HTTP POST)
4. Save

### Step 8: Test

1. Check health: `curl https://your-app.up.railway.app/`
2. Call your Twilio number from any phone
3. Check logs in the Railway dashboard

---

## Option 2: Render

### Step 1: Create Web Service

1. Go to [render.com](https://render.com/) and connect your GitHub repo
2. Create a new "Web Service"
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`

### Step 2: Add Environment Variables

Same variables as Railway (see above).

### Step 3: Deploy and Configure Twilio

Same as Railway steps 7-8 above, using your Render URL.

---

## Option 3: Fly.io

### Step 1: Install flyctl

```bash
curl -L https://fly.io/install.sh | sh
fly auth login
```

### Step 2: Create a Dockerfile

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 3: Deploy

```bash
fly launch
fly secrets set TWILIO_ACCOUNT_SID=... TWILIO_AUTH_TOKEN=... GEMINI_API_KEY=...
fly deploy
```

### Step 4: Configure Twilio

Set your Twilio webhook to your Fly.io URL.

---

## Production Checklist

After deployment, verify:

- [ ] `GET /` returns `{"status": "ok"}`
- [ ] `POST /voice` returns TwiML XML with `<Stream>`
- [ ] Twilio webhook is configured correctly
- [ ] A test call connects and you hear the greeting
- [ ] Speech recognition works (check logs for "STT transcript:")
- [ ] Gemini responds (check logs for response text)
- [ ] Audio plays back to the caller

## Production Hardening

| Area | Recommendation |
|------|---------------|
| Database | Switch to managed PostgreSQL (`DATABASE_URL=postgresql://...`) |
| Logging | Set `LOG_LEVEL=WARNING` to reduce noise |
| Secrets | Use platform secret managers, never commit `.env` |
| HTTPS | All platforms above provide HTTPS automatically |
| Monitoring | Check platform dashboards for error rates and latency |
| Scaling | Railway and Render support horizontal scaling for concurrent calls |
| STT Limit | The 5-minute Google STT streaming limit needs a restart mechanism for long calls |
