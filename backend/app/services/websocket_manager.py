"""
websocket_manager.py

Manages all active WebSocket connections for VoxAgent AI.

Responsibilities:
- Accept client connections
- Disconnect clients
- Send messages to one client
- Broadcast messages
- Track active voice sessions

No AI logic belongs here.
"""

from fastapi import WebSocket
from typing import Dict
import asyncio


class WebSocketManager:
    def __init__(self):
        # session_id -> websocket
        self.active_connections: Dict[str, WebSocket] = {}

        # Prevent race conditions
        self._lock = asyncio.Lock()

    async def connect(
        self,
        session_id: str,
        websocket: WebSocket,
    ):
        """
        Accept a new websocket connection.
        """

        await websocket.accept()

        async with self._lock:
            self.active_connections[session_id] = websocket

    async def disconnect(
        self,
        session_id: str,
    ):
        """
        Remove a websocket connection.
        """

        async with self._lock:
            self.active_connections.pop(session_id, None)

    async def send_json(
        self,
        session_id: str,
        payload: dict,
    ) -> bool:
        """
        Send JSON to one connected client.

        Returns:
            True if delivered
            False if session doesn't exist
        """

        websocket = self.active_connections.get(session_id)

        if websocket is None:
            return False

        try:
            await websocket.send_json(payload)
            return True

        except Exception:
            await self.disconnect(session_id)
            return False

    async def send_text(
        self,
        session_id: str,
        message: str,
    ) -> bool:
        websocket = self.active_connections.get(session_id)

        if websocket is None:
            return False

        try:
            await websocket.send_text(message)
            return True

        except Exception:
            await self.disconnect(session_id)
            return False

    async def broadcast(
        self,
        payload: dict,
    ):
        """
        Broadcast JSON to every connected client.
        """

        disconnected = []

        for session_id, websocket in self.active_connections.items():

            try:

                await websocket.send_json(payload)

            except Exception:

                disconnected.append(session_id)

        for session_id in disconnected:
            await self.disconnect(session_id)

    def is_connected(
        self,
        session_id: str,
    ) -> bool:

        return session_id in self.active_connections

    def connection_count(self) -> int:

        return len(self.active_connections)

    def list_sessions(self):

        return list(self.active_connections.keys())


websocket_manager = WebSocketManager()