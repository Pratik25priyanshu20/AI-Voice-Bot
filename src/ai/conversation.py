"""Conversation orchestrator tying together STT, LLM, TTS, and DB logging."""

import asyncio
import json
import time
from typing import Any, Callable, Dict, Optional

from fastapi import WebSocket

from src.ai.context import ConversationContext
from src.ai.gemini_client import GeminiClient, GeminiResponse
from src.business.handlers import BusinessHandlers
from src.database.call_logger import log_call_end, log_call_start, log_message, log_metrics
from src.speech.audio_utils import encode_base64_audio
from src.speech.google_stt import GoogleSTT
from src.speech.google_tts import GoogleTTS
from src.utils.helpers import chunk_bytes
from src.utils.logger import get_logger

logger = get_logger(__name__)

MAX_TOOL_ROUNDS = 3

# Maps tool names to BusinessHandlers method names
TOOL_METHOD_MAP: Dict[str, str] = {
    "check_order_status": "check_order_status",
    "book_appointment": "book_appointment",
    "get_faq_answer": "get_faq_answer",
}


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
        await log_call_start(self.call_sid)
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
        await log_call_end(self.call_sid)
        await self.cleanup()

    async def handle_user_input(self, transcript: str) -> None:
        """Process user speech text with tool dispatch loop."""
        logger.info("User said: %s", transcript)
        self.context.add_message("user", transcript)
        await log_message(self.call_sid, "user", transcript)

        turn_start = time.monotonic()

        # Initial LLM call
        llm_start = time.monotonic()
        result = await self.gemini.generate_response(
            self.context.to_gemini_format(), transcript
        )
        llm_elapsed_ms = int((time.monotonic() - llm_start) * 1000)

        # Tool dispatch loop — max MAX_TOOL_ROUNDS consecutive function calls
        rounds = 0
        while result.is_function_call and rounds < MAX_TOOL_ROUNDS:
            rounds += 1
            logger.info(
                "Tool call %d: %s(%s)", rounds, result.function_call, result.function_args
            )
            tool_result = await self._execute_tool(result.function_call, result.function_args)

            llm_start = time.monotonic()
            result = await self.gemini.send_function_result(
                self.context.to_gemini_format(),
                result.function_call,
                tool_result,
            )
            llm_elapsed_ms += int((time.monotonic() - llm_start) * 1000)

        # We now have a text response
        response_text = result.text or "I'm sorry, I couldn't process that."
        self.context.add_message("model", response_text)
        await log_message(self.call_sid, "assistant", response_text)

        # TTS
        tts_start = time.monotonic()
        await self.send_text(response_text)
        tts_elapsed_ms = int((time.monotonic() - tts_start) * 1000)

        total_elapsed_ms = int((time.monotonic() - turn_start) * 1000)

        # Log latency metrics (fire-and-forget)
        asyncio.create_task(
            log_metrics(
                self.call_sid,
                llm_latency=llm_elapsed_ms,
                tts_latency=tts_elapsed_ms,
                total_latency=total_elapsed_ms,
            )
        )

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Dispatch a tool call to the appropriate BusinessHandlers method."""
        method_name = TOOL_METHOD_MAP.get(tool_name)
        if not method_name:
            logger.warning("Unknown tool: %s", tool_name)
            return {"error": f"Unknown tool: {tool_name}"}
        method = getattr(self.handlers, method_name, None)
        if not method:
            logger.warning("Handler method not found: %s", method_name)
            return {"error": f"Handler not found: {method_name}"}
        try:
            return await method(**args)
        except Exception as exc:
            logger.error("Tool %s failed: %s", tool_name, exc)
            return {"error": f"Tool execution failed: {exc}"}

    async def send_text(self, text: str) -> None:
        """Convert text to audio and stream back to caller."""
        audio_bytes = await self.tts.synthesize(text)
        await self._send_audio_to_websocket(audio_bytes)

    async def _send_audio_to_websocket(self, audio: bytes) -> None:
        """Send base64 audio payload to Twilio via WebSocket, chunked for streaming."""
        if not audio:
            await self.websocket.send_json(
                {
                    "event": "media",
                    "streamSid": self.call_sid,
                    "media": {"payload": ""},
                }
            )
            return

        for chunk in chunk_bytes(audio):
            payload = encode_base64_audio(chunk)
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
