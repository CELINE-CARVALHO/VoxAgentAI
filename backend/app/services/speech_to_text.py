"""
speech_to_text.py

Groq Whisper speech-to-text integration for VoxAgent AI.
"""

from __future__ import annotations

import os
import tempfile
from typing import Optional

from groq import Groq

from app.config import settings


class SpeechToTextService:
    def __init__(self) -> None:
        self._client: Optional[Groq] = None

    def client(self) -> Groq:
        if self._client is None:
            if not settings.GROQ_API_KEY:
                raise RuntimeError("GROQ_API_KEY is missing in your .env file.")

            self._client = Groq(api_key=settings.GROQ_API_KEY)

        return self._client

    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str | None = None,
    ) -> dict:
        if not audio_bytes:
            raise ValueError("Empty audio.")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp:
            temp.write(audio_bytes)
            temp_path = temp.name

        try:
            with open(temp_path, "rb") as audio_file:
                transcription = self.client().audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3-turbo",
                    language=language,
                    response_format="verbose_json",
                )

            return {
                "text": (getattr(transcription, "text", "") or "").strip(),
                "language": getattr(transcription, "language", language or "unknown"),
                "success": True,
            }
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


speech_to_text = SpeechToTextService()
