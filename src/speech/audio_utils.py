"""Audio utility helpers."""

import base64
from typing import Optional


def decode_base64_audio(payload: str) -> bytes:
    """Decode base64-encoded audio from Twilio media streams."""
    return base64.b64decode(payload)


def encode_base64_audio(audio: bytes) -> str:
    """Encode raw audio bytes for Twilio media streams."""
    return base64.b64encode(audio).decode()


def normalize_audio(audio: bytes, expected_rate: int = 8000) -> bytes:
    """Placeholder for audio normalization/conversion."""
    return audio
