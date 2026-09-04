"""
streaming_service.py

Central orchestration layer for VoxAgent AI.

Flow:

Incoming Message
        │
        ▼
Conversation Memory
        │
        ▼
Language Detection
        │
        ▼
Knowledge Retrieval (RAG)
        │
        ▼
Prompt Builder
        │
        ▼
Groq
        │
        ▼
Response Validation
        │
        ▼
Store AI Response
        │
        ▼
Return JSON
"""

from sqlalchemy.orm import Session

from app.services.memory_service import memory_manager
from app.services.language_service import detect_language
from app.services.rag_service import retrieve_context
from app.services.prompt_builder import build_prompt
from app.services.groq_service import generate_call_turn
from app.services.response_validator import validate_response


class StreamingService:

    async def process(
        self,
        *,
        db: Session,
        session_id: str,
        user_text: str,
    ) -> dict:

        # ---------------------------------------------------------
        # Get Memory
        # ---------------------------------------------------------

        memory = memory_manager.get(session_id)

        memory.add_turn(
            speaker="user",
            message=user_text,
        )

        from app.models.call import Call
        from app.crud.call import add_transcript_turn

        call = db.query(Call).filter(Call.id == session_id).first()
        if call:
            try:
                add_transcript_turn(
                    db=db,
                    call=call,
                    speaker="user",
                    text=user_text,
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("Failed to log user transcript to DB: %s", e)

        history = memory.history()

        summary = memory.long_term_summary

        # ---------------------------------------------------------
        # Language Detection
        # ---------------------------------------------------------

        language = detect_language(user_text)

        # ---------------------------------------------------------
        # Knowledge Retrieval
        # ---------------------------------------------------------

        try:

            knowledge = retrieve_context(
                db=db,
                query=user_text,
            )

        except Exception:

            knowledge = ""

        # ---------------------------------------------------------
        # Build Prompt
        # ---------------------------------------------------------

        prompt = build_prompt(

            user_message=user_text,

            detected_language=language.language,

            knowledge_context=knowledge,

            conversation_history=history,

            long_term_summary=summary,

        )

        # ---------------------------------------------------------
        # Call Groq
        # ---------------------------------------------------------

        try:

            ai = generate_call_turn(

                user_text=prompt,

                knowledge_context="",

                conversation_history=[],

                long_term_summary="",

            )

        except Exception as e:

            ai = {

                "language": language.language,

                "intent": "general",

                "intent_confidence": 0.0,

                "sentiment": "neutral",

                "emotion": "neutral",

                "response": f"AI Error: {str(e)}",

                "entities": {},

                "should_escalate": False,

                "next_action": "none"

            }

        # ---------------------------------------------------------
        # Validate JSON
        # ---------------------------------------------------------

        ai = validate_response(ai)

        # ---------------------------------------------------------
        # Save Assistant Response
        # ---------------------------------------------------------

        memory.add_turn(

            speaker="assistant",

            message=ai["response"],

        )

        # Enforce correct language code in the response dictionary
        if ai.get("language") not in ["hi", "ta", "en"]:
            ai["language"] = language.language

        if call:
            try:
                add_transcript_turn(
                    db=db,
                    call=call,
                    speaker="ai",
                    text=ai["response"],
                    language=language.language,
                    sentiment=ai.get("sentiment", "neutral"),
                    intent=ai.get("intent", "general"),
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("Failed to log assistant transcript to DB: %s", e)

        memory.maybe_refresh_summary()

        # ---------------------------------------------------------
        # Add Metadata
        # ---------------------------------------------------------

        ai["session_id"] = session_id

        ai["detected_language"] = language.language

        ai["history_size"] = len(memory.history())

        ai["summary_available"] = bool(
            memory.long_term_summary
        )

        return ai


streaming_service = StreamingService()