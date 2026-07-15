"""
Base LLM Provider
"""

from abc import ABC
from abc import abstractmethod


class LLMProvider(ABC):

    @abstractmethod
    async def generate(
        self,
        prompt: str,
    ) -> dict:
        raise NotImplementedError