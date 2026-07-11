"""
ws.py

WebSocket router for VoxAgent AI.

Responsibilities:
- Accept WebSocket connections
- Receive messages
- Send responses
- Handle connect/disconnect

AI processing will be added later.
"""

from django import db
from fastapi import APIRouter
from fastapi import WebSocket
from fastapi import WebSocketDisconnect

from app.services.websocket_manager import websocket_manager
from backend.app.services import streaming_service

router = APIRouter(
    tags=["WebSocket"]
)


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
):

    await websocket_manager.connect(
        session_id,
        websocket,
    )

    print(f"[CONNECTED] {session_id}")

    try:

        while True:

            data = await websocket.receive_text()

            response = await streaming_service.process(

                db=db,

                session_id=session_id,

                user_text=data

            )

            await websocket.send_json(response) 

    except WebSocketDisconnect:

        print(f"[DISCONNECTED] {session_id}")

        await websocket_manager.disconnect(session_id)

    except Exception as e:

        print(f"[ERROR] {e}")

        await websocket_manager.disconnect(session_id)