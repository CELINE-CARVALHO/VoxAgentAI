"""
ws.py

WebSocket router for live VoxAgent voice sessions.
"""

import json
import logging

from fastapi import APIRouter
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from fastapi import Query
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
    token: str = Query(None),
):
    await websocket_manager.connect(session_id, websocket)
    logger.info("WebSocket connected: %s", session_id)

    db: Session = SessionLocal()

    # 1. Decode token to find owner_id (if authenticated)
    owner_id = None
    if token:
        try:
            from app.services.security import decode_access_token
            owner_id = decode_access_token(token)
        except Exception:
            pass

    # 2. Ensure call exists in the database
    try:
        from app.models.call import Call
        from app.crud.call import create_call
        from app.schemas.call import CallStartRequest

        call = db.query(Call).filter(Call.id == session_id).first()
        if not call:
            payload = CallStartRequest(caller_name="Voice User")
            create_call(db, payload=payload, owner_id=owner_id, call_id=session_id)
    except Exception as e:
        logger.warning("Failed to initialize call record in DB: %s", e)

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
        # 3. Clean up and finalize the Call in DB
        try:
            from app.crud.call import end_call, save_call_summary
            from app.models.call import Call
            from app.services.groq_service import generate_call_summary

            call = db.query(Call).filter(Call.id == session_id).first()
            if call and call.status == "active":
                call = end_call(db, call)
                try:
                    history = [{"speaker": t.speaker, "text": t.text} for t in call.transcripts]
                    if history:
                        summary_result = generate_call_summary(history)
                        if summary_result:
                            save_call_summary(db, call, summary_result["summary"])
                except Exception as summary_exc:
                    logger.warning("Summary generation failed on WS disconnect for call %s: %s", session_id, summary_exc)
        except Exception as e:
            logger.warning("Failed to end call in DB on websocket disconnect: %s", e)

        db.close()
        memory_manager.clear(session_id)
        await websocket_manager.disconnect(session_id)
