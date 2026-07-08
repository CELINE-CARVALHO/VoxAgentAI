import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict

from app.schemas.transcript import TranscriptOut


class CallStartRequest(BaseModel):
    caller_name: Optional[str] = "Unknown Caller"
    phone_number: Optional[str] = None


class MessageRequest(BaseModel):
    text: str


class MessageResponse(BaseModel):
    reply: str
    language: str
    intent: str
    sentiment: str
    latency_ms: int


class CallStartResponse(BaseModel):
    call: "CallOut"
    greeting: MessageResponse


class CallOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    call_ref: str
    caller_name: Optional[str]
    phone_number: Optional[str]
    status: str
    language: Optional[str]
    intent: Optional[str]
    sentiment: Optional[str]
    duration_seconds: Optional[int]
    avg_latency_ms: Optional[float]
    started_at: datetime
    ended_at: Optional[datetime]


class CallDetailOut(CallOut):
    transcripts: List[TranscriptOut] = []


class PaginatedCalls(BaseModel):
    items: List[CallOut]
    total: int
    page: int
    page_size: int


CallStartResponse.model_rebuild()