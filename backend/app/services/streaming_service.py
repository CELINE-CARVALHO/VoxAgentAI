"""
streaming_service.py

Central AI streaming pipeline.

Responsibilities

Browser
      │
      ▼
WebSocket
      │
      ▼
Streaming Service
      │
      ├── Conversation Memory
      ├── Language Detection
      ├── Knowledge Retrieval (RAG)
      ├── Prompt Builder
      ├── Groq
      ├── Response Validation
      └── Return JSON

No frontend code belongs here.
No websocket code belongs here.
"""

from sqlalchemy.orm import Session

from app.services.memory_service import memory_manager
from app.services.language_service import detect_language
from app.services.rag_service import retrieve_context
from app.services.prompt_builder import build_prompt
from app.services.response_validator import validate_response
from app.services.groq_service import generate_call_turn


class StreamingService:

    async def process(
        self,
        *,
        db: Session,
        session_id: str,
        user_text: str,
    ) -> dict:

        # ----------------------------
        # Get conversation memory
        # ----------------------------

        memory = memory_manager.get(session_id)

        memory.add_turn(
            speaker="user",
            message=user_text,
        )

        history = memory.history()

        # ----------------------------
        # Detect language
        # ----------------------------

        language = detect_language(user_text)

        # ----------------------------
        # Retrieve Knowledge
        # ----------------------------

        context = retrieve_context(
            db=db,
            query=user_text,
        )

        # ----------------------------
        # Build Prompt
        # ----------------------------

        prompt = build_prompt(
            user_message=user_text,
            conversation_history=history,
            knowledge_context=context,
            detected_language=language.language,
        )

        # ----------------------------
        # Call Groq
        # ----------------------------

        ai = generate_call_turn(
            prompt=prompt
        )

        # ----------------------------
        # Validate AI Response
        # ----------------------------

        ai = validate_response(ai)

        # ----------------------------
        # Save AI Response
        # ----------------------------

        memory.add_turn(
            speaker="assistant",
            message=ai["response"],
        )

        # ----------------------------
        # Add Local Metadata
        # ----------------------------

        ai["detected_language"] = language.language

        ai["session_id"] = session_id

        return ai


streaming_service = StreamingService()