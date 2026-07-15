"""
ws.py

WebSocket router for live VoxAgent voice sessions.
"""

import json
import logging

from fastapi import APIRouter
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.memory_service import memory_manager
from app.services.streaming_service import streaming_service
from app.services.websocket_manager import websocket_manager

router = APIRouter(tags=["WebSocket"])
logger = logging.getLogger(__name__)


def _parse_text_message(raw_text: str) -> tuple[str, str | None]:
    """
    Returns (message_type, text).
    """
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        return "message", raw_text

    if not isinstance(payload, dict):
        return "message", raw_text

    message_type = str(payload.get("type") or "message")

    if message_type == "ping":
        return "ping", None

    return message_type, str(payload.get("text") or "")


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
):
    await websocket_manager.connect(session_id, websocket)
    logger.info("WebSocket connected: %s", session_id)

    db: Session = SessionLocal()

    try:
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                raise WebSocketDisconnect

            if "text" in message:
                message_type, user_text = _parse_text_message(message["text"])

                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue

                if not user_text or not user_text.strip():
                    continue

                response = await streaming_service.process(
                    db=db,
                    session_id=session_id,
                    user_text=user_text.strip(),
                )

                await websocket.send_json(response)
                continue

            if "bytes" in message:
                await websocket.send_json(
                    {
                        "type": "info",
                        "message": "Upload audio through /api/voice/transcribe, then send text on this socket.",
                    }
                )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", session_id)
    except Exception as exc:
        logger.exception("WebSocket error for session %s", session_id)

        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": str(exc),
                }
            )
        except Exception:
            pass
    finally:
        db.close()
        memory_manager.clear(session_id)
        await websocket_manager.disconnect(session_id)
