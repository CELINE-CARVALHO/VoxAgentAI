"""
memory_service.py

Conversation memory manager for VoxAgent AI.

Responsibilities:
- Store recent conversation turns
- Limit history size
- Build conversation context
- Keep a rolling summary placeholder

No AI models are used here.
"""

from dataclasses import dataclass, field
from typing import List, Dict
from collections import deque


MAX_RECENT_TURNS = 10


@dataclass
class ConversationMemory:
    """
    Stores memory for one conversation.
    """

    recent_turns: deque = field(
        default_factory=lambda: deque(maxlen=MAX_RECENT_TURNS)
    )

    long_term_summary: str = ""

    def add_turn(
        self,
        speaker: str,
        message: str
    ) -> None:

        self.recent_turns.append({
            "speaker": speaker,
            "message": message
        })

    def history(self) -> List[Dict]:
        return list(self.recent_turns)

    def clear(self) -> None:
        self.recent_turns.clear()
        self.long_term_summary = ""


class MemoryManager:

    def __init__(self):
        self.sessions = {}

    def get(self, session_id: str) -> ConversationMemory:

        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationMemory()

        return self.sessions[session_id]

    def clear(self, session_id: str):

        if session_id in self.sessions:
            del self.sessions[session_id]


memory_manager = MemoryManager()