"""
Live Call Simulator + Call Logs + Conversation transcript viewer — all backed
by the same Call/Transcript tables. This is the real-backend counterpart to
the frontend's self-contained js/calls.js mock pipeline: same state machine
(start/message/end), but language/intent/sentiment/response now come from
Gemini instead of the in-browser keyword detector.
"""
import logging
from typing import Optional


from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.call import Call
from app.schemas.call import (
    CallStartRequest, MessageRequest, MessageResponse, CallStartResponse,
    CallOut, CallDetailOut, PaginatedCalls,
)
from app.crud.call import create_call, add_transcript_turn, end_call, save_call_summary
from app.services.groq_service import generate_call_turn, generate_greeting, generate_call_summary
from app.services.rag_service import retrieve_context
from app.services import memory_service

router = APIRouter(prefix="/api/calls", tags=["calls"])
logger = logging.getLogger(__name__)


@router.post("/start", response_model=CallStartResponse, status_code=201)
def start_call(
    payload: CallStartRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    call = create_call(db, payload, owner_id=current_user.id)

    from app.models.setting import Setting
    lang_hint = "en"
    user_setting = db.query(Setting).filter(Setting.user_id == current_user.id).first()
    if user_setting and isinstance(user_setting.preferences, dict):
        lang_hint = user_setting.preferences.get("default_language", "en")

    try:
        greeting = generate_greeting(language_hint=lang_hint)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM greeting failed: {exc}")

    # Enforce correct language code in the greeting dictionary
    if greeting.get("language") not in ["hi", "ta", "en"]:
        greeting["language"] = lang_hint

    add_transcript_turn(
        db, call, speaker="ai", text=greeting["response"],
        language=greeting.get("language", "en"), sentiment=greeting.get("sentiment", "neutral"),
        intent=greeting.get("intent", "greeting"), latency_ms=greeting.get("latency_ms"),
    )

    greeting_out = MessageResponse(
        reply=greeting["response"],
        language=greeting.get("language", "en"),
        intent=greeting.get("intent", "greeting"),
        sentiment=greeting.get("sentiment", "neutral"),
        latency_ms=greeting.get("latency_ms", 0),
    )
    return CallStartResponse(call=CallOut.model_validate(call), greeting=greeting_out)


@router.get("/{call_id}", response_model=CallDetailOut)
def get_call(call_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@router.post("/{call_id}/message", response_model=MessageResponse)
def send_message(
    call_id: str,
    payload: MessageRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    if call.status != "active":
        raise HTTPException(status_code=400, detail="Call is not active")

    # 1. Log the caller's utterance immediately
    add_transcript_turn(db, call, speaker="user", text=payload.text)

    # 2. Ground the response in the knowledge base
    context = retrieve_context(db, payload.text)

    # 3. Assemble conversation memory: recent turns (verbatim) + rolling
    #    long-term summary of everything older + the RAG context above.
    #    Replaces the previous approach of passing every transcript in the
    #    call unbounded and letting the LLM service silently truncate it.
    memory = memory_service.get_memory_bundle(db, call, rag_context=context)

    # 4. Ask the LLM for language + intent + sentiment + response in one call
    try:
        result = generate_call_turn(
            payload.text,
            knowledge_context=memory["rag_context"],
            conversation_history=memory["recent_turns"],
            long_term_summary=memory["long_term_summary"],
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {exc}")

    # 5. Log the AI's turn
    add_transcript_turn(
        db, call, speaker="ai", text=result["response"],
        language=result.get("language", "en"), sentiment=result.get("sentiment", "neutral"),
        intent=result.get("intent", "general_inquiry"), latency_ms=result.get("latency_ms"),
    )

    return MessageResponse(
        reply=result["response"],
        language=result.get("language", "en"),
        intent=result.get("intent", "general_inquiry"),
        sentiment=result.get("sentiment", "neutral"),
        latency_ms=result.get("latency_ms", 0),
    )


@router.post("/{call_id}/end", response_model=CallOut)
def end_call_route(call_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    call = end_call(db, call)

    # Post-call summary is best-effort: a slow/unavailable LLM should never
    # block the caller from ending the call or seeing it in Call Logs.
    try:
        history = [{"speaker": t.speaker, "text": t.text} for t in call.transcripts]
        summary_result = generate_call_summary(history)
        if summary_result:
            call = save_call_summary(db, call, summary_result["summary"])
    except Exception as exc:
        logger.warning("Call summary generation failed for call %s: %s", call_id, exc)

    return call


@router.get("", response_model=PaginatedCalls)
def list_calls(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    status: Optional[str] = Query(None, description="active | completed | missed"),
    language: Optional[str] = None,
    search: Optional[str] = Query(None, description="matches caller name, phone, or call ref"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    q = db.query(Call)

    if status:
        q = q.filter(Call.status == status)
    if language:
        q = q.filter(Call.language == language)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(
            Call.caller_name.ilike(like),
            Call.phone_number.ilike(like),
            Call.call_ref.ilike(like),
        ))

    total = q.count()
    items = (
        q.order_by(Call.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedCalls(items=items, total=total, page=page, page_size=page_size)


@router.delete("/{call_id}", status_code=204)
def delete_call(call_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    db.delete(call)
    db.commit()