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
from app.services.response_validator import validate_response

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
    long_term_summary: str = "",
):
    """
    conversation_history is expected to already be the recent-turns window
    the caller wants sent verbatim (see services/memory_service.py) — this
    function no longer re-slices it, so the caller controls the window size
    instead of two different constants disagreeing with each other.
    """
    client = _client_instance()

    history = ""

    if conversation_history:
        history = "\n".join(
            f"{m['speaker']}: {m['text']}"
            for m in conversation_history
        )

    summary_block = (
        f"""
Long-Term Summary (earlier parts of this call):

{long_term_summary}
"""
        if long_term_summary
        else ""
    )

    prompt = f"""
Knowledge Base:

{knowledge_context}
{summary_block}
Recent Conversation:

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
    parsed = validate_response(parsed)


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


MEMORY_SUMMARY_SYSTEM_PROMPT = """
You are VoxAgent AI's rolling conversation memory summarizer.

You maintain a running summary of an in-progress customer support voice call
so the AI can remember earlier parts of a long call without re-reading the
full transcript every turn.

You will be given:
1. The existing summary so far (may be empty, if this is the first refresh).
2. A new slice of conversation turns that just aged out of the recent window.

Rules:

1. Plain text only. No markdown, no JSON, no headings, no bullet lists.
2. Merge the new turns into the existing summary — do not just append,
   actually integrate them so the result reads as one coherent summary.
3. Keep it factual. Do not invent details that are not in the turns given.
4. Preserve concrete facts a later turn might need: names, order/ticket
   numbers, stated problems, promises made, decisions reached.
5. Keep it as short as possible while preserving those facts — target
   4 to 8 sentences even as the call grows longer; compress older,
   already-summarized material further to make room for new facts.
6. Write in English regardless of the language the call is happening in.
"""


def update_memory_summary(existing_summary: str, new_turns: list) -> Optional[str]:
    """
    Folds `new_turns` (list of {"speaker", "text"} dicts, chronological) into
    `existing_summary`, returning the updated rolling summary, or None if
    there was nothing to summarize or the LLM call failed to produce text.

    This is called by services/memory_service.py, not directly by routers.
    """
    if not new_turns:
        return existing_summary or None

    client = _client_instance()

    new_turns_text = "\n".join(
        f"{turn['speaker']}: {turn['text']}" for turn in new_turns
    )

    user_content = f"""
Existing Summary:

{existing_summary or "(none yet — this is the first refresh)"}

New Turns To Merge In:

{new_turns_text}
"""

    completion = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        temperature=0.2,
        max_tokens=250,
        messages=[
            {"role": "system", "content": MEMORY_SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )

    updated = (completion.choices[0].message.content or "").strip()
    return updated or (existing_summary or None)