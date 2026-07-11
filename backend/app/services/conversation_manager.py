"""
conversation_manager.py

Central orchestration layer for VoxAgent AI.

This module coordinates every AI component.
It does NOT implement business logic itself.
"""

from typing import Any, Dict, List, Optional

from app.services.language_service import detect_language
from app.services.rag_service import retrieve_context
from app.services.prompt_builder import build_prompt
from app.services.groq_service import generate_call_turn


class ConversationManager:
    """
    Main AI pipeline coordinator.
    """

    def __init__(self):
        pass

    def process(
        self,
        user_text: str,
        conversation_history: Optional[List[dict]] = None,
    ) -> Dict[str, Any]:

        # 1. Language Detection
        language = detect_language(user_text)

        # 2. Retrieve RAG Context
        context = retrieve_context(user_text)

        # 3. Build Prompt
        prompt = build_prompt(
            user_text=user_text,
            knowledge_context=context,
            conversation_history=conversation_history or [],
        )

        # 4. Generate AI Response
        response = generate_call_turn(
            user_text=user_text,
            knowledge_context=context,
            conversation_history=conversation_history or [],
        )

        return {
            "language": language,
            "rag_context": context,
            "response": response,
        }


conversation_manager = ConversationManager()