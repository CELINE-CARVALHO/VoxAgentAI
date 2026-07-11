"""
call_orchestrator.py

Central orchestration layer for VoxAgent AI.

Coordinates all backend AI services.
"""

from sqlalchemy.orm import Session

from app.services.language_service import detect_language
from app.services.memory_service import memory_manager
from app.services.rag_service import retrieve_context

from app.services.prompt_builder import build_prompt

from app.services.groq_service import generate_call_turn

from app.services.response_validator import validate_response


class CallOrchestrator:

    def process(

        self,

        db: Session,

        session_id: str,

        user_text: str,

    ):

        # -------------------------
        # Language Detection
        # -------------------------

        language = detect_language(user_text)

        # -------------------------
        # Conversation Memory
        # -------------------------

        memory = memory_manager.get(session_id)

        memory.add_turn("user", user_text)

        history = memory.history()

        # -------------------------
        # Knowledge Retrieval
        # -------------------------

        context = retrieve_context(
            db=db,
            query=user_text
        )

        # -------------------------
        # Prompt
        # -------------------------

        prompt = build_prompt(
            user_text=user_text,
            knowledge_context=context,
            conversation_history=history,
        )

        # -------------------------
        # LLM
        # -------------------------

        ai = generate_call_turn(
            prompt=prompt
        )

        ai = validate_response(ai)

        # -------------------------
        # Save AI Response
        # -------------------------

        memory.add_turn(
            "assistant",
            ai["response"]
        )

        ai["detected_language"] = language.language

        return ai


call_orchestrator = CallOrchestrator()