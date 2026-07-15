from pydantic import BaseModel
from typing import Optional


class VoiceResponse(BaseModel):
    success: bool
    message: str

    filename: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    duration_seconds: Optional[float] = None

    transcription: Optional[str] = None
    language: Optional[str] = None