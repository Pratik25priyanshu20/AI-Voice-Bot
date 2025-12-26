from fastapi import APIRouter, Request, Response, WebSocket

from src.telephony.audio_stream import handle_audio_stream
from src.telephony.twilio_handler import handle_incoming_call

router = APIRouter()


@router.get("/")
async def root() -> dict:
    return {"status": "ok", "message": "AI Voice Bot is running"}


@router.post("/voice")
async def voice_webhook(request: Request) -> Response:
    # Twilio posts call metadata here; we respond with TwiML
    twiml = handle_incoming_call()
    return Response(content=twiml, media_type="application/xml")


@router.post("/status")
async def status_callback() -> dict:
    return {"status": "received"}


@router.websocket("/ws/audio-stream/{call_sid}")
async def websocket_endpoint(websocket: WebSocket, call_sid: str) -> None:
    await handle_audio_stream(websocket, call_sid)
