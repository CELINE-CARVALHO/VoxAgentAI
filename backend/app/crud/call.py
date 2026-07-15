import random
import string
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.call import Call
from app.models.transcript import Transcript
from app.schemas.call import CallStartRequest


def generate_call_ref() -> str:
    return "CALL-" + "".join(random.choices(string.digits, k=6))


def create_call(db: Session, payload: CallStartRequest, owner_id=None, call_id=None) -> Call:
    kwargs = {
        "call_ref": generate_call_ref(),
        "caller_name": payload.caller_name or "Unknown Caller",
        "phone_number": payload.phone_number,
        "status": "active",
        "owner_id": owner_id,
    }
    if call_id:
        kwargs["id"] = call_id
    call = Call(**kwargs)
    db.add(call)
    db.commit()
    db.refresh(call)
    return call


def add_transcript_turn(
    db: Session,
    call: Call,
    speaker: str,
    text: str,
    language: str | None = None,
    sentiment: str | None = None,
    intent: str | None = None,
    latency_ms: int | None = None,
) -> Transcript:
    turn = Transcript(
        call_id=call.id,
        speaker=speaker,
        text=text,
        language=language,
        sentiment=sentiment,
        intent=intent,
        latency_ms=latency_ms,
    )
    db.add(turn)

    # Keep the call row's "last known" language/intent/sentiment in sync —
    # this is what the Dashboard/Call Logs list views read.
    if language:
        call.language = language
    if intent:
        call.intent = intent
    if sentiment:
        call.sentiment = sentiment

    db.commit()
    db.refresh(turn)
    return turn


def end_call(db: Session, call: Call) -> Call:
    call.status = "completed"
    call.ended_at = datetime.utcnow()
    if call.started_at:
        call.duration_seconds = int((call.ended_at - call.started_at).total_seconds())

    latencies = [t.latency_ms for t in call.transcripts if t.latency_ms]
    if latencies:
        call.avg_latency_ms = sum(latencies) / len(latencies)

    db.commit()
    db.refresh(call)
    return call


def save_call_summary(db: Session, call: Call, summary: str) -> Call:
    call.summary = summary
    call.summary_generated_at = datetime.utcnow()
    db.commit()
    db.refresh(call)
    return call