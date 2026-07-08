"""Per-account settings (Settings page) stored as flexible key/value rows."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Setting(Base):
    __tablename__ = "settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)

    # Free-form JSON blob: voice, default_language, notification prefs,
    # business hours, escalation email, etc. Kept flexible so the frontend
    # settings form can evolve without new migrations for every field.
    preferences = Column(JSON, nullable=False, default=dict)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)