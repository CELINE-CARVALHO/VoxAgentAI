"""
Groq LLM integration for VoxAgent AI.

This replaces gemini_service.py while keeping exactly the same public API
used by routers/calls.py.

Returned JSON:

{
    "language": "...",
    "intent": "...",
    "sentiment": "...",
    "response": "...",
    "latency_ms": 123
}
"""

import json
import re
import time
from typing import Optional

from groq import Groq

from app.config import settings

_client = None


def _client_instance():
    global _client

    if _client is None:
        if not settings.GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is missing in your .env file."
            )

        _client = Groq(api_key=settings.GROQ_API_KEY)

    return _client


SYSTEM_PROMPT = """
You are VoxAgent AI.

You are an AI customer support voice assistant.

Always answer ONLY with valid JSON.

Never wrap the JSON in markdown.

Output format:

{
  "language":"en",
  "intent":"general_inquiry",
  "sentiment":"neutral",
  "response":"..."
}

Rules:

1. Detect caller language.
2. Detect caller intent.
3. Detect sentiment.
4. Respond in the SAME language.
5. Use the supplied knowledge base context.
6. If the answer is unavailable, politely say you don't know and suggest contacting a human.
"""


def _extract_json(text: str) -> dict:
    text = text.strip()

    text = re.sub(
        r"^```(?:json)?",
        "",
        text,
        flags=re.MULTILINE,
    )

    text = re.sub(
        r"```$",
        "",
        text,
        flags=re.MULTILINE,
    )

    return json.loads(text.strip())


def generate_call_turn(
    user_text: str,
    knowledge_context: str = "",
    conversation_history: Optional[list] = None,
):
    client = _client_instance()

    history = ""

    if conversation_history:
        history = "\n".join(
            f"{m['speaker']}: {m['text']}"
            for m in conversation_history[-6:]
        )

    prompt = f"""
Knowledge Base:

{knowledge_context}

Conversation:

{history}

Caller:

{user_text}
"""

    start = time.perf_counter()

    completion = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        temperature=0.3,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    latency = int((time.perf_counter() - start) * 1000)

    result = _extract_json(
        completion.choices[0].message.content
    )

    result["latency_ms"] = latency

    return result


def generate_greeting(language_hint: str = "en"):
    client = _client_instance()

    prompt = f"""
Start a new phone call.

Reply in language:

{language_hint}

Return JSON only.

Intent must be greeting.

Sentiment must be neutral.
"""

    start = time.perf_counter()

    completion = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    latency = int((time.perf_counter() - start) * 1000)

    result = _extract_json(
        completion.choices[0].message.content
    )

    result["latency_ms"] = latency

    return result