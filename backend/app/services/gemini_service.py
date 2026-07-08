"""
Real LLM integration (Google Gemini) — replaces the frontend's mock keyword
detector. One Gemini call does language detection + intent classification +
sentiment analysis + response generation together, returning strict JSON,
so a full call turn only costs a single round trip.
"""
import json
import re
import time
from typing import Optional

import google.generativeai as genai

from app.config import settings

_configured = False


def _ensure_configured():
    global _configured
    if not _configured:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your .env file before "
                "starting a live call."
            )
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _configured = True


SYSTEM_INSTRUCTIONS = """You are the AI voice agent for VoxAgent AI, a customer support \
call-center product. You are grounded ONLY in the knowledge base context provided to you \
— if the context doesn't answer the question, say so politely and offer to escalate to a \
human agent rather than inventing details.

Always reply with ONLY a single valid JSON object (no markdown fences, no extra prose) \
with exactly these keys:
{
  "language": "<ISO 639-1 code of the language the caller used, e.g. en, es, fr, hi>",
  "intent": "<one short snake_case label, e.g. order_status, refund_request, billing_issue, \
general_inquiry, complaint, greeting, farewell>",
  "sentiment": "<one of: positive, neutral, negative>",
  "response": "<your reply to the caller, written in the SAME language they used, \
concise and conversational — this will be spoken aloud via text-to-speech>"
}"""


def _extract_json(raw_text: str) -> dict:
    """Gemini sometimes wraps JSON in ```json fences despite instructions — strip them."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def generate_call_turn(
    user_text: str,
    knowledge_context: str = "",
    conversation_history: Optional[list] = None,
) -> dict:
    """
    Returns a dict: {language, intent, sentiment, response, latency_ms}
    Raises RuntimeError / json.JSONDecodeError on failure — callers should
    catch and fall back gracefully (see routers/calls.py).
    """
    _ensure_configured()

    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=SYSTEM_INSTRUCTIONS,
    )

    history_block = ""
    if conversation_history:
        lines = [f"{turn['speaker'].upper()}: {turn['text']}" for turn in conversation_history[-6:]]
        history_block = "Conversation so far:\n" + "\n".join(lines) + "\n\n"

    context_block = (
        f"Knowledge base context (use this to ground your answer):\n{knowledge_context}\n\n"
        if knowledge_context
        else "Knowledge base context: (none available — answer generally and offer escalation "
        "if the question needs specific account/order details)\n\n"
    )

    prompt = f"{history_block}{context_block}Caller just said: \"{user_text}\""

    start = time.perf_counter()
    result = model.generate_content(prompt)
    latency_ms = int((time.perf_counter() - start) * 1000)

    parsed = _extract_json(result.text)
    parsed["latency_ms"] = latency_ms
    return parsed


def generate_greeting(language_hint: str = "en") -> dict:
    """Kick-off greeting when a call starts, mirroring the frontend's opener."""
    _ensure_configured()
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=SYSTEM_INSTRUCTIONS,
    )
    prompt = (
        "The call has just started, no caller message yet. Produce a short, warm greeting "
        f"opener in language '{language_hint}' asking how you can help today. Set intent to "
        "'greeting' and sentiment to 'neutral'."
    )
    start = time.perf_counter()
    result = model.generate_content(prompt)
    latency_ms = int((time.perf_counter() - start) * 1000)
    parsed = _extract_json(result.text)
    parsed["latency_ms"] = latency_ms
    return parsed