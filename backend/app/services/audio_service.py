"""
Audio Service

Current Responsibilities

✓ Validate uploads
✓ Save temporary audio
✓ Return metadata

Future

✓ Streaming
✓ ASR
✓ Voice Activity Detection
✓ Noise Removal
"""

import os
import uuid

from fastapi import UploadFile

UPLOAD_FOLDER = "temp_audio"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


class AudioService:

    ALLOWED_TYPES = {

        "audio/webm",

        "audio/wav",

        "audio/mpeg",

        "audio/mp3",

        "audio/ogg"

    }

    async def save_audio(
        self,
        file: UploadFile
    ):

        if file.content_type not in self.ALLOWED_TYPES:

            raise ValueError(
                f"Unsupported file type: {file.content_type}"
            )

        extension = file.filename.split(".")[-1]

        filename = f"{uuid.uuid4()}.{extension}"

        filepath = os.path.join(
            UPLOAD_FOLDER,
            filename
        )

        data = await file.read()

        with open(filepath, "wb") as f:
            f.write(data)

        return {

            "filename": filename,

            "filepath": filepath,

            "size_bytes": len(data),

            "content_type": file.content_type

        }


audio_service = AudioService()