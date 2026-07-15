"""
audio_ws.py

Streaming audio WebSocket endpoint.

Current phase:
- Accept binary audio chunks.
- Accept JSON control messages.
- Prepare for ASR integration.

Future:
- Streaming ASR
- Streaming TTS
- Barge-in
- Telephony
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.websocket_manager import websocket_manager
from app.services.voice_pipeline import voice_pipeline

router = APIRouter(tags=["Audio WebSocket"])


@router.websocket("/ws/audio/{session_id}")
async def audio_websocket(
    websocket: WebSocket,
    session_id: str,
):

    await websocket_manager.connect(session_id, websocket)

    print(f"[AUDIO CONNECTED] {session_id}")

    try:

        while True:

            message = await websocket.receive()

            #
            # Binary audio
            #

            if "bytes" in message:

                audio = message["bytes"]

                #
                # Phase 5:
                # Just acknowledge receipt.
                #

                await websocket.send_json(
                    {
                        "type": "audio_received",
                        "size": len(audio),
                    }
                )

            #
            # Text / JSON control
            #

            elif "text" in message:

                text = message["text"]

                if text == "ping":

                    await websocket.send_json(
                        {
                            "type": "pong"
                        }
                    )

                else:

                    await websocket.send_json(
                        {
                            "type": "info",
                            "message": text,
                        }
                    )

    except WebSocketDisconnect:

        print(f"[AUDIO DISCONNECTED] {session_id}")

        await websocket_manager.disconnect(session_id)

    except Exception as e:

        print(e)

        try:

            await websocket.send_json(
                {
                    "type": "error",
                    "message": str(e),
                }
            )

        except Exception:
            pass

        await websocket_manager.disconnect(session_id)