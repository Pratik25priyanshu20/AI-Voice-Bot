"""Text-to-Speech using Google Cloud TTS with MULAW 8kHz output."""

import asyncio
from typing import Optional

from google.cloud import texttospeech

from src.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleTTS:
    """Google Cloud Text-to-Speech with MULAW 8kHz for Twilio."""

    def __init__(self, sample_rate: int = 8000):
        self.sample_rate = sample_rate
        try:
            self._client = texttospeech.TextToSpeechClient()
        except Exception as exc:
            logger.error("Failed to create TTS client: %s", exc)
            self._client = None

        self._voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
        )
        self._audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MULAW,
            sample_rate_hertz=self.sample_rate,
        )

    def _synthesize_sync(self, text: str) -> bytes:
        """Synchronous TTS call — run via asyncio.to_thread()."""
        if not self._client:
            logger.warning("TTS client not available")
            return b""
        try:
            input_text = texttospeech.SynthesisInput(text=text)
            response = self._client.synthesize_speech(
                input=input_text,
                voice=self._voice,
                audio_config=self._audio_config,
            )
            return response.audio_content
        except Exception as exc:
            logger.error("TTS synthesis failed: %s", exc)
            return b""

    async def synthesize(self, text: str) -> bytes:
        """Return synthesized MULAW 8kHz audio bytes."""
        if not text or not text.strip():
            return b""
        logger.info("Synthesizing TTS for text: %s", text[:80])
        return await asyncio.to_thread(self._synthesize_sync, text)

    def audio_format(self) -> dict[str, Optional[int]]:
        """Return playback config for downstream streaming."""
        return {"sample_rate": self.sample_rate}
