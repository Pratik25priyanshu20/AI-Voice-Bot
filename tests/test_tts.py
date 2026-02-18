"""Tests for Google TTS wrapper."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.speech.google_tts import GoogleTTS


@pytest.fixture
def mock_tts_client():
    """Patch the TextToSpeechClient so no real credentials are needed."""
    with patch("src.speech.google_tts.texttospeech") as mock_tts_mod:
        mock_client_instance = MagicMock()
        mock_tts_mod.TextToSpeechClient.return_value = mock_client_instance

        # Stub enums/configs so GoogleTTS.__init__ works
        mock_tts_mod.VoiceSelectionParams.return_value = "voice_params"
        mock_tts_mod.AudioConfig.return_value = "audio_config"
        mock_tts_mod.AudioEncoding.MULAW = "MULAW"
        mock_tts_mod.SsmlVoiceGender.NEUTRAL = "NEUTRAL"
        mock_tts_mod.SynthesisInput.return_value = "synth_input"

        yield mock_client_instance, mock_tts_mod


def test_synthesize_returns_audio_bytes(mock_tts_client):
    client_instance, mock_mod = mock_tts_client
    fake_audio = b"\x00\x01\x02\x03" * 100
    client_instance.synthesize_speech.return_value = MagicMock(audio_content=fake_audio)

    tts = GoogleTTS(sample_rate=8000)
    result = asyncio.get_event_loop().run_until_complete(tts.synthesize("Hello"))

    assert result == fake_audio
    client_instance.synthesize_speech.assert_called_once()


def test_synthesize_empty_text_returns_empty(mock_tts_client):
    tts = GoogleTTS()
    result = asyncio.get_event_loop().run_until_complete(tts.synthesize(""))
    assert result == b""


def test_synthesize_whitespace_returns_empty(mock_tts_client):
    tts = GoogleTTS()
    result = asyncio.get_event_loop().run_until_complete(tts.synthesize("   "))
    assert result == b""


def test_synthesize_handles_api_error(mock_tts_client):
    client_instance, _ = mock_tts_client
    client_instance.synthesize_speech.side_effect = Exception("API error")

    tts = GoogleTTS()
    result = asyncio.get_event_loop().run_until_complete(tts.synthesize("Test"))

    assert result == b""


def test_audio_format(mock_tts_client):
    tts = GoogleTTS(sample_rate=8000)
    fmt = tts.audio_format()
    assert fmt == {"sample_rate": 8000}


def test_client_creation_failure():
    """If client creation fails, synthesize degrades gracefully."""
    with patch("src.speech.google_tts.texttospeech") as mock_mod:
        mock_mod.TextToSpeechClient.side_effect = Exception("No credentials")
        mock_mod.VoiceSelectionParams.return_value = "vp"
        mock_mod.AudioConfig.return_value = "ac"
        mock_mod.AudioEncoding.MULAW = "MULAW"
        mock_mod.SsmlVoiceGender.NEUTRAL = "NEUTRAL"

        tts = GoogleTTS()
        result = asyncio.get_event_loop().run_until_complete(tts.synthesize("Hello"))
        assert result == b""
