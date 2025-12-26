"""Gemini client wrapper."""

import asyncio
from typing import List

import google.generativeai as genai

from config.prompts import SYSTEM_PROMPT
from config.settings import settings
from src.business.tools import AVAILABLE_TOOLS
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GeminiClient:
    """Lightweight async wrapper for Gemini calls."""

    def __init__(self):
        if settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            tools=AVAILABLE_TOOLS,
            system_instruction=SYSTEM_PROMPT.strip(),
            generation_config={
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 150,
            },
        )

    async def generate_response(self, history: List[dict], user_message: str) -> str:
        """Send conversation history to Gemini and return text."""
        if not settings.gemini_api_key:
            logger.warning("GEMINI_API_KEY not configured; returning fallback response.")
            return "I am not fully configured yet, but I am here to help."

        async def _run() -> str:
            try:
                chat = self.model.start_chat(history=history)
                response = chat.send_message(user_message)
                return response.text or "I am here to help."
            except Exception as exc:  # pragma: no cover - third-party dependency
                logger.error("Gemini call failed: %s", exc)
                return "I'm having trouble processing that. Could you repeat?"

        return await asyncio.to_thread(_run)
