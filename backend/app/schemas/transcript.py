import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TranscriptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    speaker: str
    text: str
    language: Optional[str] = None
    sentiment: Optional[str] = None
    intent: Optional[str] = None
    latency_ms: Optional[int] = None
    created_at: datetime    