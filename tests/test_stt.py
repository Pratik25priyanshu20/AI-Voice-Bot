"""Tests for Google STT wrapper."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.speech.google_stt import GoogleSTT


@pytest.fixture
def mock_stt_client():
    """Patch the SpeechClient so no real credentials are needed."""
    with patch("src.speech.google_stt.speech") as mock_speech_mod:
        mock_client_instance = MagicMock()
        mock_speech_mod.SpeechClient.return_value = mock_client_instance

        # Stub config objects
        mock_speech_mod.RecognitionConfig.return_value = "rec_config"
        mock_speech_mod.RecognitionConfig.AudioEncoding.MULAW = "MULAW"
        mock_speech_mod.StreamingRecognitionConfig.return_value = "stream_config"
        mock_speech_mod.StreamingRecognizeRequest = MagicMock

        yield mock_client_instance, mock_speech_mod


def test_get_transcript_returns_none_when_empty(mock_stt_client):
    stt = GoogleSTT()
    result = asyncio.get_event_loop().run_until_complete(stt.get_transcript())
    assert result is None


def test_get_transcript_returns_queued_item(mock_stt_client):
    stt = GoogleSTT()
    # Manually push a transcript
    stt._transcripts.put_nowait("Hello world")
    result = asyncio.get_event_loop().run_until_complete(stt.get_transcript())
    assert result == "Hello world"


def test_get_transcript_with_timeout(mock_stt_client):
    stt = GoogleSTT()
    stt._transcripts.put_nowait("Hi there")
    result = asyncio.get_event_loop().run_until_complete(stt.get_transcript(timeout=1.0))
    assert result == "Hi there"


def test_get_transcript_timeout_returns_none(mock_stt_client):
    stt = GoogleSTT()
    result = asyncio.get_event_loop().run_until_complete(stt.get_transcript(timeout=0.1))
    assert result is None


def test_process_audio_chunk_queues_data(mock_stt_client):
    stt = GoogleSTT()
    asyncio.get_event_loop().run_until_complete(stt.process_audio_chunk(b"\x00\x01"))
    assert not stt._audio_queue.empty()
    chunk = stt._audio_queue.get_nowait()
    assert chunk == b"\x00\x01"


def test_close_sets_running_false(mock_stt_client):
    stt = GoogleSTT()
    stt._running = True
    asyncio.get_event_loop().run_until_complete(stt.close())
    assert stt._running is False


def test_client_creation_failure():
    """If client creation fails, start_stream degrades gracefully."""
    with patch("src.speech.google_stt.speech") as mock_mod:
        mock_mod.SpeechClient.side_effect = Exception("No credentials")
        mock_mod.RecognitionConfig.return_value = "rc"
        mock_mod.RecognitionConfig.AudioEncoding.MULAW = "MULAW"
        mock_mod.StreamingRecognitionConfig.return_value = "sc"

        stt = GoogleSTT()
        assert stt._client is None
        # start_stream should not crash
        asyncio.get_event_loop().run_until_complete(stt.start_stream())
        assert stt._running is False
