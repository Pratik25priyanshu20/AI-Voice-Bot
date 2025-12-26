"""Text-to-Speech helper using Google Cloud (placeholder)."""

from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleTTS:
    """Minimal stub for Google Text-to-Speech."""

    def __init__(self, sample_rate: int = 8000):
        self.sample_rate = sample_rate

    async def synthesize(self, text: str) -> bytes:
        """Return synthesized audio bytes (placeholder)."""
        logger.info("Synthesizing TTS for text: %s", text)
        # In production, call Google TTS and return mulaw 8k audio
        return b""

    def audio_format(self) -> dict[str, Optional[int]]:
        """Return playback config for downstream streaming."""
        return {"sample_rate": self.sample_rate}
