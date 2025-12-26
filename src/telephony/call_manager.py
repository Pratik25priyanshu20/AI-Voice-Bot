"""Manage conversations keyed by Twilio call SID."""

from typing import Dict

from fastapi import WebSocket

from src.ai.conversation import ConversationOrchestrator

_conversations: Dict[str, ConversationOrchestrator] = {}


def get_or_create_conversation(call_sid: str, websocket: WebSocket) -> ConversationOrchestrator:
    """Return an existing orchestrator or create a new one."""
    if call_sid not in _conversations:
        _conversations[call_sid] = ConversationOrchestrator(
            call_sid=call_sid,
            websocket=websocket,
            on_cleanup=lambda: end_conversation(call_sid),
        )
    return _conversations[call_sid]


def end_conversation(call_sid: str) -> None:
    """Remove conversation from registry."""
    _conversations.pop(call_sid, None)
