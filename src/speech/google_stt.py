"""Streaming Speech-to-Text using Google Cloud Speech API."""

import asyncio
import threading
from typing import Optional

from google.cloud import speech

from src.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleSTT:
    """Google Cloud STT with streaming recognition via a background thread."""

    def __init__(self, sample_rate: int = 8000):
        self.sample_rate = sample_rate
        self._audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._transcripts: asyncio.Queue[str] = asyncio.Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        try:
            self._client = speech.SpeechClient()
        except Exception as exc:
            logger.error("Failed to create STT client: %s", exc)
            self._client = None

        self._config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.MULAW,
            sample_rate_hertz=self.sample_rate,
            language_code="en-US",
        )
        self._streaming_config = speech.StreamingRecognitionConfig(
            config=self._config,
            single_utterance=False,
        )

    async def start_stream(self) -> None:
        """Start the background recognition thread."""
        if not self._client:
            logger.warning("STT client not available; stream not started")
            return
        self._loop = asyncio.get_running_loop()
        self._running = True
        self._thread = threading.Thread(target=self._recognition_loop, daemon=True)
        self._thread.start()
        logger.info("STT stream started at %s Hz", self.sample_rate)

    def _audio_generator(self):
        """Yield audio chunks from the async queue, bridging async -> sync."""
        while self._running:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._get_audio_with_timeout(), self._loop
                )
                chunk = future.result(timeout=5.0)
                if chunk is None:
                    continue
                yield speech.StreamingRecognizeRequest(audio_content=chunk)
            except Exception:
                if not self._running:
                    break
                continue

    async def _get_audio_with_timeout(self) -> Optional[bytes]:
        """Get audio from queue with a timeout to allow shutdown checks."""
        try:
            return await asyncio.wait_for(self._audio_queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

    def _recognition_loop(self) -> None:
        """Run streaming recognition in a background thread.

        TODO: Production hardening — Google has a ~5min streaming limit.
        Add automatic restart with backoff for long-running calls.
        """
        while self._running:
            try:
                requests = self._audio_generator()
                responses = self._client.streaming_recognize(
                    self._streaming_config, requests
                )
                for response in responses:
                    if not self._running:
                        break
                    for result in response.results:
                        if result.is_final and result.alternatives:
                            transcript = result.alternatives[0].transcript.strip()
                            if transcript:
                                logger.info("STT transcript: %s", transcript)
                                asyncio.run_coroutine_threadsafe(
                                    self._transcripts.put(transcript), self._loop
                                )
            except Exception as exc:
                if self._running:
                    logger.warning("STT stream error (will restart): %s", exc)
                else:
                    break

    async def process_audio_chunk(self, audio_data: bytes) -> None:
        """Accept raw MULAW audio bytes from Twilio."""
        await self._audio_queue.put(audio_data)

    async def get_transcript(self, timeout: float = 0.0) -> Optional[str]:
        """Return the next final transcript if available."""
        try:
            if timeout:
                return await asyncio.wait_for(self._transcripts.get(), timeout=timeout)
            return self._transcripts.get_nowait()
        except Exception:
            return None

    async def close(self) -> None:
        """Shut down the recognition thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        logger.info("STT stream closed")
