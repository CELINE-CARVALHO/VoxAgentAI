"""
Prompt Builder Service

Builds the complete prompt sent to the LLM.

Responsibilities:
- System instructions
- Company policy
- Knowledge Base context
- Conversation history
- Current user message

This service contains NO model-specific code.
"""

from typing import List, Dict

MAX_HISTORY = 10


SYSTEM_PROMPT = """
You are VoxAgent AI.

You are an enterprise AI Voice Agent used by businesses to handle customer calls.

Your goals:

- Be professional.
- Be polite.
- Be concise.
- Answer only using available knowledge.
- Never hallucinate.
- If the answer isn't available,
  politely explain that you don't know
  and offer to connect the customer to a human.

Always reply in the SAME language as the user.

Always return ONLY valid JSON.

Output format:

{
    "language": "...",
    "intent": "...",
    "sentiment": "...",
    "response": "..."
}
"""


COMPANY_POLICY = """
Rules

1. Never invent company policies.

2. Never fabricate order information.

3. Never fabricate customer data.

4. Use the Knowledge Base whenever possible.

5. If information is unavailable,
   suggest escalation.

6. Keep answers conversational.

7. Keep answers under 120 words.
"""


def build_prompt(
    user_message: str,
    knowledge_context: str = "",
    conversation_history: List[Dict] | None = None,
) -> str:
    """
    Returns a single optimized prompt for Groq.
    """

    prompt = []

    # ------------------------------------------------------------------
    # System Prompt
    # ------------------------------------------------------------------

    prompt.append(SYSTEM_PROMPT)

    # ------------------------------------------------------------------
    # Company Rules
    # ------------------------------------------------------------------

    prompt.append(COMPANY_POLICY)

    # ------------------------------------------------------------------
    # Knowledge Base
    # ------------------------------------------------------------------

    if knowledge_context:

        prompt.append(
            f"""
Knowledge Base

{knowledge_context}
"""
        )

    else:

        prompt.append(
            """
Knowledge Base

No relevant knowledge was found.
"""
        )

    # ------------------------------------------------------------------
    # Conversation
    # ------------------------------------------------------------------

    if conversation_history:

        prompt.append("Conversation History")

        for turn in conversation_history[-MAX_HISTORY:]:

            speaker = turn.get("speaker", "user").upper()

            text = turn.get("text", "")

            prompt.append(f"{speaker}: {text}")

    # ------------------------------------------------------------------
    # Current Message
    # ------------------------------------------------------------------

    prompt.append(
        f"""

Current User Message

{user_message}
"""
    )

    prompt.append(
        """

Return ONLY valid JSON.

No markdown.

No explanation.
"""
    )

    return "\n".join(prompt)