"""WebSocket handler for Twilio media streams."""

import json

from fastapi import WebSocket

from src.ai.conversation import ConversationOrchestrator
from src.telephony.call_manager import get_or_create_conversation
from src.speech.audio_utils import decode_base64_audio
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def handle_audio_stream(websocket: WebSocket, call_sid: str) -> None:
    """Process Twilio Media Stream messages."""
    await websocket.accept()
    orchestrator: ConversationOrchestrator = get_or_create_conversation(call_sid, websocket)
    logger.info("WebSocket connected for call %s", call_sid)
    try:
        while True:
            raw_message = await websocket.receive_text()
            message = json.loads(raw_message)
            event = message.get("event")

            if event == "connected":
                await orchestrator.on_call_connected(message)
            elif event == "start":
                await orchestrator.on_call_started(message)
            elif event == "media":
                payload = message.get("media", {}).get("payload")
                if payload:
                    audio_bytes = decode_base64_audio(payload)
                    await orchestrator.on_audio_chunk(audio_bytes)
            elif event == "stop":
                await orchestrator.on_call_stopped(message)
                break
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Error handling stream: %s", exc)
    finally:
        await orchestrator.cleanup()
        await websocket.close()
        logger.info("WebSocket closed for call %s", call_sid)
