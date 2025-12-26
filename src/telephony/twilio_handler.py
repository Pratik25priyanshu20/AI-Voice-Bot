"""Twilio webhook utilities."""

from twilio.twiml.voice_response import Connect, Stream, VoiceResponse

from config.settings import settings


def handle_incoming_call() -> str:
    """Return TwiML that connects the caller to a media stream."""
    response = VoiceResponse()
    # Fallback greeting while stream connects
    response.say("Connecting you to our AI assistant. Please hold a moment.")
    connect = Connect()
    connect.stream(url=settings.websocket_stream_url)
    response.append(connect)
    return str(response)
