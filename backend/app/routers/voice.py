from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File
from fastapi import HTTPException

from app.schemas.voice import VoiceResponse
from app.services.audio_service import audio_service

router = APIRouter(
    prefix="/api/voice",
    tags=["Voice"]
)


@router.post(
    "/transcribe",
    response_model=VoiceResponse
)
async def transcribe_audio(
    audio: UploadFile = File(...)
):

    try:

        info = await audio_service.save_audio(audio)

        return VoiceResponse(

            success=True,

            message="Audio uploaded successfully.",

            filename=info["filename"],

            content_type=info["content_type"],

            size_bytes=info["size_bytes"],

            transcription=None

        )

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )