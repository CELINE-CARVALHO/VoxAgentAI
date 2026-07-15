"""
Base ASR Provider

Every Speech-to-Text provider must implement this interface.

Examples

- Groq Whisper API
- Deepgram
- Google Speech
- Azure Speech
- OpenAI Speech

No local models.
"""

from abc import ABC
from abc import abstractmethod


class ASRProvider(ABC):

    @abstractmethod
    async def transcribe(
        self,
        audio: bytes,
        language: str | None = None,
    ) -> dict:
        """
        Returns

        {
            "text": "...",
            "language": "...",
            "confidence":0.98
        }
        """
        raise NotImplementedError