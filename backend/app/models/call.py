"""A single voice call session — drives Live Call, Call Logs, and Dashboard/Analytics stats."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey, Text

from sqlalchemy.orm import relationship

from app.database import Base


class Call(Base):
    __tablename__ = "calls"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    call_ref = Column(String(50), unique=True, nullable=False, index=True)  # e.g. CALL-849213

    caller_name = Column(String(255), nullable=True, default="Unknown Caller")
    phone_number = Column(String(50), nullable=True)

    status = Column(String(20), nullable=False, default="active")  # active | completed | missed
    language = Column(String(10), nullable=True, default="en")     # last-detected language code
    intent = Column(String(100), nullable=True, default="general_inquiry")
    sentiment = Column(String(20), nullable=True, default="neutral")  # positive | neutral | negative

    duration_seconds = Column(Integer, nullable=True, default=0)
    avg_latency_ms = Column(Float, nullable=True, default=0)

    summary = Column(Text, nullable=True)  # AI-generated post-call summary (LLM, set on call end)
    summary_generated_at = Column(DateTime, nullable=True)

    # Rolling in-call conversation memory (Phase 3 — services/memory_service.py).
    # Distinct from `summary` above: that one is a single post-call wrap-up
    # written once when the call ends; this one is updated incrementally
    # *during* the call so the AI can recall turns that have aged out of the
    # verbatim recent-turns window it sends on every request.
    memory_summary = Column(Text, nullable=True)
    memory_summary_turns_covered = Column(Integer, nullable=False, default=0)

    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)

    owner_id = Column(
        String(36),
        ForeignKey("users.id"),
        nullable=True
    )

    transcripts = relationship(
        "Transcript", back_populates="call", cascade="all, delete-orphan",
        order_by="Transcript.created_at",
    )