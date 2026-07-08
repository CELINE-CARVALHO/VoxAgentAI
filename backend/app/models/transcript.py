"""One turn (user or AI) within a call's transcript."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer

from sqlalchemy.orm import relationship

from app.database import Base


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    call_id = Column(
        String(36),
        ForeignKey("calls.id"),
        nullable=False
    )

    speaker = Column(String(10), nullable=False)  # "user" | "ai"
    text = Column(Text, nullable=False)
    language = Column(String(10), nullable=True)
    sentiment = Column(String(20), nullable=True)
    intent = Column(String(100), nullable=True)
    latency_ms = Column(Integer, nullable=True)  # AI turns only

    created_at = Column(DateTime, default=datetime.utcnow)

    call = relationship("Call", back_populates="transcripts")