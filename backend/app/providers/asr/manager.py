"""
ASR Manager

Chooses the configured Speech Provider.

Today

Raises NotImplemented.

Future

Groq

Deepgram

Google

Azure
"""

from app.config import settings


class ASRManager:

    async def transcribe(
        self,
        audio: bytes,
        language=None,
    ):

        provider = getattr(settings, "ASR_PROVIDER", "future")

        raise NotImplementedError(
            f"ASR provider '{provider}' has not been configured."
        )


asr_manager = ASRManager()