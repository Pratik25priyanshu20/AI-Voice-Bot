"""Streaming Speech-to-Text placeholder using Google Cloud."""

import asyncio
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleSTT:
    """Minimal stub for Google STT streaming."""

    def __init__(self, sample_rate: int = 8000):
        self.sample_rate = sample_rate
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._transcripts: asyncio.Queue[str] = asyncio.Queue()

    async def start_stream(self) -> None:
        """Start processing queue; in real code this opens Google stream."""
        logger.info("STT stream initialized at %s Hz", self.sample_rate)

    async def process_audio_chunk(self, audio_data: bytes) -> None:
        """Accept raw audio bytes; placeholder just buffers."""
        await self._queue.put(audio_data)

    async def get_transcript(self, timeout: float = 0.0) -> Optional[str]:
        """Return the next transcript if available."""
        try:
            if timeout:
                return await asyncio.wait_for(self._transcripts.get(), timeout=timeout)
            return self._transcripts.get_nowait()
        except Exception:
            return None

    async def close(self) -> None:
        logger.info("STT stream closed")
