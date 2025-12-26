"""Conversation orchestrator tying together STT, LLM, and TTS."""

import asyncio
from typing import Callable, Optional

from fastapi import WebSocket

from src.ai.context import ConversationContext
from src.ai.gemini_client import GeminiClient
from src.business.handlers import BusinessHandlers
from src.speech.google_stt import GoogleSTT
from src.speech.google_tts import GoogleTTS
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ConversationOrchestrator:
    """Maintain per-call conversation flow."""

    def __init__(self, call_sid: str, websocket: WebSocket, on_cleanup: Optional[Callable[[], None]] = None):
        self.call_sid = call_sid
        self.websocket = websocket
        self._on_cleanup = on_cleanup
        self.context = ConversationContext()
        self.gemini = GeminiClient()
        self.stt = GoogleSTT()
        self.tts = GoogleTTS()
        self.handlers = BusinessHandlers()
        self.state = "greeting"

    async def on_call_connected(self, payload: dict) -> None:
        logger.info("Call %s connected", self.call_sid)

    async def on_call_started(self, payload: dict) -> None:
        logger.info("Call %s started with metadata: %s", self.call_sid, payload.get("start", {}))
        await self.stt.start_stream()
        await self.send_text("Hello! How can I help you today?")

    async def on_audio_chunk(self, audio: bytes) -> None:
        """Receive audio chunk from Twilio stream."""
        await self.stt.process_audio_chunk(audio)
        transcript = await self.stt.get_transcript()
        if transcript:
            await self.handle_user_input(transcript)

    async def on_call_stopped(self, payload: dict) -> None:
        logger.info("Call %s ended", self.call_sid)
        await self.cleanup()

    async def handle_user_input(self, transcript: str) -> None:
        """Process user speech text."""
        logger.info("User said: %s", transcript)
        self.context.add_message("user", transcript)
        response_text = await self.gemini.generate_response(self.context.to_gemini_format(), transcript)
        self.context.add_message("model", response_text)
        await self.send_text(response_text)

    async def send_text(self, text: str) -> None:
        """Convert text to audio and stream back to caller."""
        audio_bytes = await self.tts.synthesize(text)
        await self._send_audio_to_websocket(audio_bytes)

    async def _send_audio_to_websocket(self, audio: bytes) -> None:
        """Send base64 audio payload to Twilio via WebSocket."""
        if not audio:
            # Placeholder text fallback ensures call flow continues
            await self.websocket.send_json(
                {
                    "event": "media",
                    "streamSid": self.call_sid,
                    "media": {"payload": ""},
                }
            )
            return

        import base64

        payload = base64.b64encode(audio).decode()
        await self.websocket.send_json(
            {
                "event": "media",
                "streamSid": self.call_sid,
                "media": {"payload": payload},
            }
        )

    async def cleanup(self) -> None:
        """Release resources at end of call."""
        try:
            await self.stt.close()
        except Exception:
            logger.debug("STT cleanup skipped")
        if self._on_cleanup:
            try:
                self._on_cleanup()
            except Exception:
                logger.debug("Cleanup callback failed")
