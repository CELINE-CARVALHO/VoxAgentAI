"""
prompt_builder.py

Builds the final prompt sent to Groq.

Responsibilities

- System Instructions
- Company Policy
- Knowledge Base
- Long-term Memory
- Recent Conversation
- Current User Message

No API calls happen here.
"""

from typing import List, Dict

MAX_HISTORY = 10


SYSTEM_PROMPT = """
You are VoxAgent AI.

You are a multilingual enterprise AI Voice Agent for customer support.

Your responsibilities:

• Detect the caller's language.
• Detect the caller's intent.
• Detect caller sentiment.
• Detect caller emotion.
• Extract entities.
• Maintain conversation context.
• Answer naturally.
• Never hallucinate.
• Never invent company policies.
• Always use the supplied knowledge base.
• If information is unavailable,
  politely say so and suggest a human agent.

Always answer in the SAME language as the customer.

=== CRITICAL: VOICE OUTPUT / TTS ===
This assistant speaks its response aloud using browser Text-To-Speech.
The TTS engine on Windows does NOT have Tamil or Hindi Unicode voice packs.

Therefore:
• If the customer writes in Tamil (even romanized / Tanglish like "paarkal",
  "ithu aen"), respond in Tamil but write it in ROMANIZED LATIN SCRIPT
  (Tanglish). Example: "Network signal konjam weak aa iruntha ithu aagalaam."
  NOT in Unicode Tamil: “நெட்வர்க் சிக்னல்...”

• If the customer writes in Hindi (even romanized / Hinglish like "kya hoga",
  "batao"), respond in Hindi but write it in ROMANIZED LATIN SCRIPT
  (Hinglish). Example: "Network signal 2 bars hai kyunki coverage area mein
  problem ho sakti hai."
  NOT in Devanagari Unicode: “नेटवर्क...”

• For English, respond normally in English.

This ensures every caller hears a clear, natural spoken response
regardless of their device's installed voice packs.

Return ONLY valid JSON.

JSON FORMAT

{
    "language":"en",

    "intent":"general",

    "intent_confidence":0.95,

    "sentiment":"neutral",

    "emotion":"neutral",

    "entities":{

        "customer_name":"",

        "phone":"",

        "email":"",

        "order_id":""

    },

    "should_escalate":false,

    "next_action":"none",

    "response":"..."
}
"""


COMPANY_POLICY = """
Company Rules

1. Never invent policies.

2. Never invent prices.

3. Never invent order information.

4. Never invent customer information.

5. Use only supplied knowledge.

6. Keep answers conversational.

7. Maximum response:

120 words.

8. If the answer isn't known,
suggest contacting a human.

9. Never output markdown.

10. Never explain JSON.
"""


def build_prompt(
    *,
    user_message: str,
    detected_language: str,
    knowledge_context: str,
    conversation_history: List[Dict],
    long_term_summary: str = "",
) -> str:

    prompt = []

    # ------------------------------------------------
    # SYSTEM
    # ------------------------------------------------

    prompt.append(SYSTEM_PROMPT)

    # ------------------------------------------------
    # POLICY
    # ------------------------------------------------

    prompt.append(COMPANY_POLICY)

    # ------------------------------------------------
    # LANGUAGE
    # ------------------------------------------------

    prompt.append(
        f"""
Detected Language

{detected_language}
"""
    )

    # ------------------------------------------------
    # LONG TERM MEMORY
    # ------------------------------------------------

    if long_term_summary:

        prompt.append(
            f"""
Conversation Summary

{long_term_summary}
"""
        )

    # ------------------------------------------------
    # KNOWLEDGE BASE
    # ------------------------------------------------

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

No relevant knowledge available.
"""
        )

    # ------------------------------------------------
    # RECENT CONVERSATION
    # ------------------------------------------------

    if conversation_history:

        prompt.append("Recent Conversation")

        for turn in conversation_history[-MAX_HISTORY:]:

            speaker = turn.get("speaker", "user").upper()

            text = turn.get("text", "")

            prompt.append(

                f"{speaker}: {text}"

            )

    # ------------------------------------------------
    # CURRENT USER MESSAGE
    # ------------------------------------------------

    prompt.append(

        f"""

Current User Message

{user_message}

"""
    )

    # ------------------------------------------------
    # FINAL INSTRUCTION
    # ------------------------------------------------

    prompt.append(
        """
Return ONLY JSON.

Do not explain.

Do not use markdown.

Do not include code fences.
"""
    )

    return "\n".join(prompt)