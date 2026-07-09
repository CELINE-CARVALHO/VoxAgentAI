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


SUMMARY_SYSTEM_PROMPT = """
You are VoxAgent AI's post-call summarizer.

You will be given the full transcript of a customer support voice call.

Write a concise summary for a human agent who was not on the call.

Rules:

1. Plain text only. No markdown, no JSON, no headings, no bullet lists.
2. 2 to 4 sentences maximum.
3. Cover: why the caller reached out, what was resolved or discussed,
   and any follow-up action still needed (or state that none is needed).
4. Write in English regardless of the language the call happened in.
5. Be factual. Do not invent details that are not in the transcript.
"""


def generate_call_summary(transcript_turns: list) -> Optional[dict]:
    """
    Summarize a completed call for the Call Logs / Conversation views.

    transcript_turns: list of {"speaker": "user"|"ai", "text": str} dicts,
    in chronological order (typically call.transcripts from the ORM).

    Returns {"summary": str, "latency_ms": int}, or None if there is no
    transcript to summarize (e.g. a call that ended before any turns).
    """
    if not transcript_turns:
        return None

    client = _client_instance()

    conversation = "\n".join(
        f"{turn['speaker']}: {turn['text']}" for turn in transcript_turns
    )

    start = time.perf_counter()

    completion = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        temperature=0.2,
        max_tokens=200,
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": f"Transcript:\n\n{conversation}"},
        ],
    )

    latency = int((time.perf_counter() - start) * 1000)
    summary_text = (completion.choices[0].message.content or "").strip()

    if not summary_text:
        return None

    return {"summary": summary_text, "latency_ms": latency}