"""Tests for database call logger using in-memory SQLite."""

import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, Call, CallMetrics, Conversation


@pytest.fixture(autouse=True)
def in_memory_db(monkeypatch):
    """Replace SessionLocal with an in-memory SQLite session for tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    monkeypatch.setattr("src.database.call_logger.SessionLocal", TestSession)
    yield TestSession


def test_log_call_start(in_memory_db):
    from src.database.call_logger import _log_call_start_sync

    _log_call_start_sync("call-001")

    session = in_memory_db()
    call = session.query(Call).filter(Call.call_sid == "call-001").first()
    assert call is not None
    assert call.status == "active"
    assert call.start_time is not None
    session.close()


def test_log_call_end(in_memory_db):
    from src.database.call_logger import _log_call_end_sync, _log_call_start_sync

    _log_call_start_sync("call-002")
    _log_call_end_sync("call-002")

    session = in_memory_db()
    call = session.query(Call).filter(Call.call_sid == "call-002").first()
    assert call is not None
    assert call.status == "completed"
    assert call.end_time is not None
    assert call.duration is not None
    session.close()


def test_log_call_end_missing_call(in_memory_db):
    """Ending a call that doesn't exist should not crash."""
    from src.database.call_logger import _log_call_end_sync

    _log_call_end_sync("nonexistent")  # Should not raise


def test_log_message(in_memory_db):
    from src.database.call_logger import _log_message_sync

    _log_message_sync("call-003", "user", "Hello there", intent="greeting")

    session = in_memory_db()
    msg = session.query(Conversation).filter(Conversation.call_sid == "call-003").first()
    assert msg is not None
    assert msg.role == "user"
    assert msg.message == "Hello there"
    assert msg.intent == "greeting"
    session.close()


def test_log_metrics(in_memory_db):
    from src.database.call_logger import _log_metrics_sync

    _log_metrics_sync("call-004", stt_latency=50, llm_latency=200, tts_latency=100, total_latency=350)

    session = in_memory_db()
    metrics = session.query(CallMetrics).filter(CallMetrics.call_sid == "call-004").first()
    assert metrics is not None
    assert metrics.llm_latency == 200
    assert metrics.tts_latency == 100
    assert metrics.total_latency == 350
    session.close()


def test_async_wrappers_delegate_to_sync(monkeypatch):
    """Verify async wrappers call their sync counterparts via to_thread."""
    from unittest.mock import AsyncMock, patch

    import src.database.call_logger as mod

    calls = []

    def fake_sync_start(call_sid):
        calls.append(("start", call_sid))

    def fake_sync_message(call_sid, role, message, intent=None):
        calls.append(("message", call_sid, role, message))

    monkeypatch.setattr(mod, "_log_call_start_sync", fake_sync_start)
    monkeypatch.setattr(mod, "_log_message_sync", fake_sync_message)

    asyncio.get_event_loop().run_until_complete(mod.log_call_start("call-async"))
    asyncio.get_event_loop().run_until_complete(
        mod.log_message("call-async", "assistant", "Hi!")
    )

    assert ("start", "call-async") in calls
    assert ("message", "call-async", "assistant", "Hi!") in calls
