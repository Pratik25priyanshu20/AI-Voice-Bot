# Deployment Guide

## Platform options
- **Railway** (recommended): simple, free starter tier.
- Render / Fly.io: similar setup; use the provided Procfile.

## Steps (Railway)
1. Push your code to GitHub.
2. Create a new Railway project and connect the repo.
3. Add environment variables from `.env` in the Railway Variables tab.
4. Ensure your service uses the `Procfile` command:
   ```
   web: uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
   ```
5. Deploy; wait for build to finish.
6. Grab the public URL and set your Twilio voice webhook to `https://<your-app>/voice`.

## Post-deploy checklist
- Health check (`GET /`) returns status `ok`.
- Twilio webhook hits `/voice` and receives TwiML.
- Media stream WebSocket connects from Twilio to `/ws/audio-stream/{call_sid}`.
- Logs show conversations flowing end-to-end.

## Hardening tips
- Set `LOG_LEVEL=INFO` or `WARNING` in production.
- Use a managed Postgres instance and update `DATABASE_URL`.
- Store secrets only in your hosting provider's secret manager.
- Add HTTPS termination (Railway handles this automatically).
