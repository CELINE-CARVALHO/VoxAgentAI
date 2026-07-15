"""
Base TTS Provider
"""

from abc import ABC
from abc import abstractmethod


class TTSProvider(ABC):

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        language: str,
        voice: str | None = None,
    ) -> bytes:
        """
        Returns audio bytes.
        """
        raise NotImplementedError