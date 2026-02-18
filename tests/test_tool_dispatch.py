"""Tests for tool dispatch loop in ConversationOrchestrator."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.gemini_client import GeminiResponse


@pytest.fixture
def orchestrator():
    """Create an orchestrator with mocked dependencies."""
    with patch("src.ai.conversation.GoogleSTT"), \
         patch("src.ai.conversation.GoogleTTS") as MockTTS, \
         patch("src.ai.conversation.GeminiClient") as MockGemini, \
         patch("src.ai.conversation.log_call_start", new_callable=AsyncMock), \
         patch("src.ai.conversation.log_call_end", new_callable=AsyncMock), \
         patch("src.ai.conversation.log_message", new_callable=AsyncMock), \
         patch("src.ai.conversation.log_metrics", new_callable=AsyncMock):

        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()

        # TTS returns fake audio
        MockTTS.return_value.synthesize = AsyncMock(return_value=b"\x00" * 100)

        from src.ai.conversation import ConversationOrchestrator

        orch = ConversationOrchestrator(call_sid="test-123", websocket=mock_ws)
        yield orch


def test_text_response_no_tool_call(orchestrator):
    """When Gemini returns text directly, no tool dispatch happens."""
    orchestrator.gemini.generate_response = AsyncMock(
        return_value=GeminiResponse(text="Your order is on the way!")
    )

    asyncio.get_event_loop().run_until_complete(
        orchestrator.handle_user_input("Where is my order?")
    )

    orchestrator.gemini.generate_response.assert_called_once()
    # send_function_result should NOT be called
    assert not hasattr(orchestrator.gemini.send_function_result, "called") or \
        not orchestrator.gemini.send_function_result.called


def test_single_tool_call_then_text(orchestrator):
    """Gemini returns a function_call, then text after receiving the result."""
    # First call: function call
    orchestrator.gemini.generate_response = AsyncMock(
        return_value=GeminiResponse(
            function_call="check_order_status",
            function_args={"order_number": "12345"},
        )
    )
    # Second call (after function result): text
    orchestrator.gemini.send_function_result = AsyncMock(
        return_value=GeminiResponse(text="Order 12345 has shipped!")
    )

    asyncio.get_event_loop().run_until_complete(
        orchestrator.handle_user_input("Check order 12345")
    )

    orchestrator.gemini.generate_response.assert_called_once()
    orchestrator.gemini.send_function_result.assert_called_once()


def test_max_tool_rounds_respected(orchestrator):
    """Tool loop should stop after MAX_TOOL_ROUNDS even if Gemini keeps requesting tools."""
    func_response = GeminiResponse(
        function_call="check_order_status",
        function_args={"order_number": "999"},
    )
    orchestrator.gemini.generate_response = AsyncMock(return_value=func_response)
    orchestrator.gemini.send_function_result = AsyncMock(return_value=func_response)

    asyncio.get_event_loop().run_until_complete(
        orchestrator.handle_user_input("Check order 999")
    )

    # 1 initial call + MAX_TOOL_ROUNDS send_function_result calls
    from src.ai.conversation import MAX_TOOL_ROUNDS
    assert orchestrator.gemini.send_function_result.call_count == MAX_TOOL_ROUNDS


def test_unknown_tool_returns_error(orchestrator):
    """An unknown tool name should produce an error result, not crash."""
    orchestrator.gemini.generate_response = AsyncMock(
        return_value=GeminiResponse(
            function_call="nonexistent_tool",
            function_args={},
        )
    )
    orchestrator.gemini.send_function_result = AsyncMock(
        return_value=GeminiResponse(text="I couldn't find that tool.")
    )

    asyncio.get_event_loop().run_until_complete(
        orchestrator.handle_user_input("Do something weird")
    )

    # Verify the function result was sent (with the error)
    call_args = orchestrator.gemini.send_function_result.call_args
    result_arg = call_args[1].get("result") or call_args[0][2]
    assert "error" in str(result_arg).lower() or "unknown" in str(result_arg).lower()


def test_tool_execution_error_handled(orchestrator):
    """If a tool raises an exception, it's caught and reported gracefully."""
    orchestrator.gemini.generate_response = AsyncMock(
        return_value=GeminiResponse(
            function_call="check_order_status",
            function_args={"order_number": "BAD"},
        )
    )
    orchestrator.handlers.check_order_status = AsyncMock(side_effect=RuntimeError("DB down"))
    orchestrator.gemini.send_function_result = AsyncMock(
        return_value=GeminiResponse(text="Sorry, I couldn't look that up right now.")
    )

    asyncio.get_event_loop().run_until_complete(
        orchestrator.handle_user_input("Check order BAD")
    )

    orchestrator.gemini.send_function_result.assert_called_once()
