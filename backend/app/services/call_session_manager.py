"""
call_session_manager.py

Maintains the runtime state of every active conversation.

Prototype Version

Responsibilities
----------------
- Active sessions
- Current language
- Transcript
- Last activity
- Conversation metadata

NOTE:
This is in-memory only.
No Redis.
No database persistence.

Perfect for the prototype.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class TranscriptTurn:
    speaker: str
    text: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CallSession:

    session_id: str

    language: str = "en"

    intent: str = "general"

    sentiment: str = "neutral"

    transcript: List[TranscriptTurn] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.utcnow)

    updated_at: datetime = field(default_factory=datetime.utcnow)

    metadata: Dict = field(default_factory=dict)

    def add_turn(self, speaker: str, text: str):

        self.transcript.append(

            TranscriptTurn(

                speaker=speaker,

                text=text,

            )

        )

        self.updated_at = datetime.utcnow()

    def history(self):

        return [

            {

                "speaker": turn.speaker,

                "text": turn.text,

                "timestamp": turn.timestamp.isoformat(),

            }

            for turn in self.transcript

        ]


class CallSessionManager:

    def __init__(self):

        self.sessions: Dict[str, CallSession] = {}

    # -----------------------------------------------------

    def get(self, session_id: str) -> CallSession:

        if session_id not in self.sessions:

            self.sessions[session_id] = CallSession(

                session_id=session_id

            )

        return self.sessions[session_id]

    # -----------------------------------------------------

    def exists(self, session_id: str) -> bool:

        return session_id in self.sessions

    # -----------------------------------------------------

    def remove(self, session_id: str):

        self.sessions.pop(session_id, None)

    # -----------------------------------------------------

    def clear(self):

        self.sessions.clear()

    # -----------------------------------------------------

    def total_sessions(self):

        return len(self.sessions)


call_session_manager = CallSessionManager()