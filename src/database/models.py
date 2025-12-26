"""SQLAlchemy models for call logging and metrics."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    call_sid = Column(String, unique=True, index=True)
    phone_number = Column(String)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)  # seconds
    status = Column(String, default="active")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    call_sid = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    role = Column(String)  # user or assistant
    message = Column(Text)
    intent = Column(String, nullable=True)


class CallMetrics(Base):
    __tablename__ = "call_metrics"

    id = Column(Integer, primary_key=True, index=True)
    call_sid = Column(String, index=True)
    stt_latency = Column(Integer, nullable=True)
    llm_latency = Column(Integer, nullable=True)
    tts_latency = Column(Integer, nullable=True)
    total_latency = Column(Integer, nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
