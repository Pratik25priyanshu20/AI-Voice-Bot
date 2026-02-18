"""Async-safe database logging helpers for call lifecycle and metrics."""

import asyncio
from datetime import datetime
from typing import Optional

from src.database.db import SessionLocal
from src.database.models import Call, CallMetrics, Conversation
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ── Sync helpers (each manages its own session) ──────────────────────────


def _log_call_start_sync(call_sid: str) -> None:
    session = SessionLocal()
    try:
        session.add(Call(call_sid=call_sid, start_time=datetime.utcnow()))
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error("DB log_call_start failed: %s", exc)
    finally:
        session.close()


def _log_call_end_sync(call_sid: str) -> None:
    session = SessionLocal()
    try:
        call = session.query(Call).filter(Call.call_sid == call_sid).first()
        if call:
            call.end_time = datetime.utcnow()
            if call.start_time:
                call.duration = int((call.end_time - call.start_time).total_seconds())
            call.status = "completed"
            session.commit()
        else:
            logger.warning("No call row found for %s on end", call_sid)
    except Exception as exc:
        session.rollback()
        logger.error("DB log_call_end failed: %s", exc)
    finally:
        session.close()


def _log_message_sync(
    call_sid: str, role: str, message: str, intent: Optional[str] = None
) -> None:
    session = SessionLocal()
    try:
        session.add(
            Conversation(
                call_sid=call_sid,
                role=role,
                message=message,
                intent=intent,
                timestamp=datetime.utcnow(),
            )
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error("DB log_message failed: %s", exc)
    finally:
        session.close()


def _log_metrics_sync(
    call_sid: str,
    stt_latency: Optional[int] = None,
    llm_latency: Optional[int] = None,
    tts_latency: Optional[int] = None,
    total_latency: Optional[int] = None,
) -> None:
    session = SessionLocal()
    try:
        session.add(
            CallMetrics(
                call_sid=call_sid,
                stt_latency=stt_latency,
                llm_latency=llm_latency,
                tts_latency=tts_latency,
                total_latency=total_latency,
                created_at=datetime.utcnow(),
            )
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error("DB log_metrics failed: %s", exc)
    finally:
        session.close()


# ── Async wrappers ───────────────────────────────────────────────────────


async def log_call_start(call_sid: str) -> None:
    await asyncio.to_thread(_log_call_start_sync, call_sid)


async def log_call_end(call_sid: str) -> None:
    await asyncio.to_thread(_log_call_end_sync, call_sid)


async def log_message(
    call_sid: str, role: str, message: str, intent: Optional[str] = None
) -> None:
    await asyncio.to_thread(_log_message_sync, call_sid, role, message, intent)


async def log_metrics(
    call_sid: str,
    stt_latency: Optional[int] = None,
    llm_latency: Optional[int] = None,
    tts_latency: Optional[int] = None,
    total_latency: Optional[int] = None,
) -> None:
    await asyncio.to_thread(
        _log_metrics_sync, call_sid, stt_latency, llm_latency, tts_latency, total_latency
    )
