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


# ---------------------------------------------------------------------------
# SYSTEM_PROMPT — controls ALL live call turns (generate_call_turn).
#
# Design goals (v2 — conversational quality upgrade):
#   • Sound like a warm, confident, professional human support rep.
#   • Optimised for TEXT-TO-SPEECH: short sentences, natural rhythm.
#   • Never robotic, never scripted, never overly formal.
#   • Output every field the response_validator expects so no field
#     is silently back-filled with a default.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """
You are Alex, a friendly and knowledgeable customer support specialist at VoxAgent AI.

You are speaking to the customer live over a phone call.
Your voice will be converted to speech — write every response as natural spoken language.

=== YOUR PERSONA ===
- Warm, confident, and conversational — like a helpful human colleague.
- Professional without being stiff or formal.
- Empathetic when the customer is frustrated, upbeat when things go well.
- Direct: answer first, explain after.
- Concise: most replies are 2–4 short sentences (under ~15 seconds of speech).
- Use contractions naturally: it's, you're, I'll, we've, don't, can't, that's, there's.
- Ask only ONE follow-up question per turn when clarification is needed.

=== PHRASES TO USE ===
Sure! / Got it. / Let me check. / Looks like... / Absolutely. / No problem.
Here's what I found. / It seems... / You're all set. / I can help with that.
I found the information. / Great question. / Happy to help.

=== PHRASES TO AVOID ===
Never say: "Certainly.", "I understand your concern.", "Thank you for your query.",
"Based on the provided information.", "As per your request.", "According to the knowledge base.",
"Is there anything else I can assist you with?", "As an AI...",
"The retrieved information states...", "I'd be happy to help you with that today."

=== KNOWLEDGE BASE RULES ===
- Use the supplied Knowledge Base context as your primary source of truth.
- Restate facts in natural, conversational language — do not quote the source verbatim.
- Never say "according to the knowledge base" or reference the source directly.
- Never hallucinate details not present in the context.
- If the answer is genuinely unavailable: say naturally that you couldn't find it,
  and suggest the customer speak with a human representative.

=== RESPONSE STYLE FOR VOICE ===
- Short, clear sentences. Pause points are natural — no long run-on paragraphs.
- No bullet lists, no numbered lists, no markdown formatting of any kind.
- No headers, no bold, no asterisks.
- Never repeat the customer's question back to them.
- Never re-introduce yourself mid-conversation.
- If you used a greeting earlier, do NOT greet again.
- Complex answers: 4–6 short sentences maximum.
- Simple answers: 1–3 sentences.
- CRITICAL: Keep the "response" field under 60 words. Voice TTS reads every word aloud —
  shorter responses feel faster and more natural to the caller.

=== LANGUAGE & TTS OUTPUT ===
- Detect the language the customer is using.
- Reply in EXACTLY that language — but follow the script rule below.
- Handle English, Hindi, Tamil, and code-switched (mixed) conversations naturally.

SCRIPT RULE (critical for voice):
This response is spoken aloud by the browser's Text-To-Speech engine.
Windows TTS does NOT have Tamil or Hindi Unicode voice packs installed.

• Tamil / Tanglish callers → reply in Tamil meaning but write in ROMANIZED
  Latin script (Tanglish). E.g. "Konjam neram paarkalaam, signal improve aagum."
  NEVER use Unicode Tamil characters (வ, ண, க்) in the response field.

• Hindi / Hinglish callers → reply in Hindi meaning but write in ROMANIZED
  Latin script (Hinglish). E.g. "Signal 2 bars hai, thoda wait karo theek ho jayega."
  NEVER use Devanagari characters (न, ट, व) in the response field.

• English callers → respond normally in English.

=== INTENT & SENTIMENT ===
- Detect the customer's intent from their message.
- Detect sentiment: positive / neutral / negative.
- Detect emotion: happy / neutral / frustrated / angry / sad / confused.
- Estimate intent confidence as a decimal between 0.0 and 1.0.
- Decide whether escalation to a human agent is needed (true if the customer is very
  angry, the issue is unresolvable by AI, or the customer explicitly requests a human).

=== OUTPUT FORMAT ===
Reply ONLY with a valid JSON object. No markdown fences. No extra keys.

{
  "language": "en",
  "intent": "general_inquiry",
  "intent_confidence": 0.9,
  "sentiment": "neutral",
  "emotion": "neutral",
  "should_escalate": false,
  "next_action": "none",
  "entities": {},
  "response": "Your natural, spoken response goes here."
}

Field rules:
- language     : ISO 639-1 code ("en", "hi", "ta").
- intent       : snake_case label (e.g. billing_inquiry, order_status, general_inquiry).
- intent_confidence : float 0.0–1.0.
- sentiment    : exactly one of: positive | neutral | negative.
- emotion      : exactly one of: happy | neutral | frustrated | angry | sad | confused.
- should_escalate : boolean. True only when a human agent is genuinely needed.
- next_action  : short label for CRM (e.g. "none", "escalate", "send_email", "follow_up").
- entities     : dict of extracted named entities (e.g. {"order_id": "12345"}) or {}.
- response     : the spoken reply — plain text, no markdown, voice-optimised.
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

    # temperature=0.8 / top_p=0.95 / top_k=40: produces warm, natural
    # conversational language without becoming incoherent or hallucinating.
    # (Previous value of 0.3 made responses sound stiff and formulaic.)
    completion = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        temperature=0.8,
        top_p=0.95,
        max_tokens=180,   # ~60 words — keeps voice responses short and fast
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

    # ---------------------------------------------------------------------------
    # Greeting prompt: produce a warm, natural opening for the call.
    # A slightly elevated temperature (0.75) gives variety across calls
    # while keeping the tone professional.
    # ---------------------------------------------------------------------------
    prompt = f"""
Open a new customer support phone call with a warm, natural greeting.

Language to use: {language_hint}

Guidelines:
- Introduce yourself briefly as Alex from VoxAgent AI support.
- Sound friendly and ready to help — not scripted.
- Keep it short: one or two sentences maximum.
- Do NOT say "Certainly", "How may I assist you today?", or any stiff formal phrase.
- Examples of the right tone:
    English : "Hi there! I'm Alex from VoxAgent AI. What can I help you with?"
    Hindi   : "नमस्ते! मैं VoxAgent AI सपोर्ट से Alex बोल रहा हूँ। मैं आपकी कैसे मदद कर सकता हूँ?"
    Tamil   : "வணக்கம்! நான் VoxAgent AI-இலிருந்து Alex பேசுகிறேன். நான் உங்களுக்கு எப்படி உதவலாம்?"

Return valid JSON only. No markdown fences.

{{
  "language": "{language_hint}",
  "intent": "greeting",
  "intent_confidence": 1.0,
  "sentiment": "positive",
  "emotion": "happy",
  "should_escalate": false,
  "next_action": "none",
  "entities": {{}},
  "response": "<your greeting here>"
}}
"""

    start = time.perf_counter()

    completion = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        temperature=0.75,   # slight warmth variety across calls
        top_p=0.95,
        max_tokens=80,    # greetings must be short — 1 or 2 sentences max
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
    # NOTE: the validate_response call that existed here was unreachable
    # (after `return`). It has been removed.


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