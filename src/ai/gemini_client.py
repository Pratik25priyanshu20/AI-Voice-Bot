"""Gemini client wrapper with structured responses and tool calling support."""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from config.prompts import SYSTEM_PROMPT
from config.settings import settings
from src.business.tools import AVAILABLE_TOOLS
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class GeminiResponse:
    """Structured response from Gemini — either text or a function call."""

    text: Optional[str] = None
    function_call: Optional[str] = None
    function_args: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_function_call(self) -> bool:
        return self.function_call is not None


class GeminiClient:
    """Lightweight async wrapper for Gemini calls with tool-calling support."""

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

    def _parse_response(self, response) -> GeminiResponse:
        """Extract text or function call from a Gemini response."""
        for part in response.parts:
            if hasattr(part, "function_call") and part.function_call.name:
                fc = part.function_call
                args = dict(fc.args) if fc.args else {}
                return GeminiResponse(function_call=fc.name, function_args=args)
        # No function call — return text
        text = response.text if response.text else "I am here to help."
        return GeminiResponse(text=text)

    async def generate_response(
        self, history: List[dict], user_message: str
    ) -> GeminiResponse:
        """Send conversation history to Gemini and return structured response."""
        if not settings.gemini_api_key:
            logger.warning("GEMINI_API_KEY not configured; returning fallback response.")
            return GeminiResponse(text="I am not fully configured yet, but I am here to help.")

        def _run() -> GeminiResponse:
            try:
                chat = self.model.start_chat(history=history)
                response = chat.send_message(user_message)
                return self._parse_response(response)
            except Exception as exc:
                logger.error("Gemini call failed: %s", exc)
                return GeminiResponse(
                    text="I'm having trouble processing that. Could you repeat?"
                )

        return await asyncio.to_thread(_run)

    async def send_function_result(
        self,
        history: List[dict],
        function_name: str,
        result: Any,
    ) -> GeminiResponse:
        """Send a function result back to Gemini and return the next response."""
        if not settings.gemini_api_key:
            return GeminiResponse(text="I am not fully configured yet, but I am here to help.")

        def _run() -> GeminiResponse:
            try:
                chat = self.model.start_chat(history=history)
                response = chat.send_message(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=function_name,
                            response={"result": result},
                        )
                    )
                )
                return self._parse_response(response)
            except Exception as exc:
                logger.error("Gemini function result call failed: %s", exc)
                return GeminiResponse(
                    text="I'm having trouble processing that. Could you repeat?"
                )

        return await asyncio.to_thread(_run)
