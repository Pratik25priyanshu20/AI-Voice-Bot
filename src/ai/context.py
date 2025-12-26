"""Conversation context and history management."""

from collections import deque
from typing import Deque, Dict, List


class ConversationContext:
    """Track recent conversation history for prompting."""

    def __init__(self, max_turns: int = 10):
        self.history: Deque[Dict[str, str]] = deque(maxlen=max_turns * 2)  # user + assistant per turn

    def add_message(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})

    def get_history(self) -> List[Dict[str, str]]:
        return list(self.history)

    def to_gemini_format(self) -> List[Dict[str, str]]:
        return [{"role": item["role"], "parts": [item["content"]]} for item in self.history]
