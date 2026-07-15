from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File
from fastapi import HTTPException

from app.schemas.voice import VoiceResponse
from app.services.audio_service import audio_service
from app.services.speech_to_text import speech_to_text

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
        
        with open(info["filepath"], "rb") as f:
            audio_bytes = f.read()
            
        transcription_result = await speech_to_text.transcribe(audio_bytes=audio_bytes)

        return VoiceResponse(

            success=True,

            message="Audio uploaded and transcribed successfully.",

            filename=info["filename"],

            content_type=info["content_type"],

            size_bytes=info["size_bytes"],

            transcription=transcription_result.get("text"),
            
            language=transcription_result.get("language")

        )

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )