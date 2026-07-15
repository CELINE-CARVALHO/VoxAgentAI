"""
TTS Manager
"""

from app.config import settings


class TTSManager:

    async def synthesize(
        self,
        text,
        language,
        voice=None,
    ):

        provider = getattr(settings, "TTS_PROVIDER", "future")

        raise NotImplementedError(
            f"TTS provider '{provider}' has not been configured."
        )


tts_manager = TTSManager()