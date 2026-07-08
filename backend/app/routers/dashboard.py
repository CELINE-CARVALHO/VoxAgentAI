"""Dashboard page: top stat cards + system health status row."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.call import Call
from app.models.knowledge import KnowledgeDocument
from app.config import settings

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def dashboard_stats(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    calls_today = db.query(func.count(Call.id)).filter(Call.started_at >= today_start).scalar() or 0
    calls_yesterday = (
        db.query(func.count(Call.id))
        .filter(Call.started_at >= yesterday_start, Call.started_at < today_start)
        .scalar() or 0
    )
    delta_pct = (
        round(((calls_today - calls_yesterday) / calls_yesterday) * 100, 1)
        if calls_yesterday else None
    )

    active_calls = db.query(func.count(Call.id)).filter(Call.status == "active").scalar() or 0
    avg_latency = db.query(func.avg(Call.avg_latency_ms)).filter(Call.avg_latency_ms.isnot(None)).scalar() or 0
    avg_duration = db.query(func.avg(Call.duration_seconds)).filter(Call.duration_seconds.isnot(None)).scalar() or 0
    kb_doc_count = db.query(func.count(KnowledgeDocument.id)).scalar() or 0

    return {
        "calls_today": calls_today,
        "calls_today_delta_pct": delta_pct,
        "active_calls": active_calls,
        "avg_latency_ms": round(float(avg_latency), 1),
        "avg_duration_seconds": round(float(avg_duration), 1),
        "knowledge_documents": kb_doc_count,
    }


@router.get("/status")
def dashboard_status(current_user=Depends(get_current_user)):
    """
    Simple health check row: DB (implicit — we got this far), and whether the
    Gemini API key is configured. A real deployment could ping STT/TTS
    providers here too.
    """
    return {
        "database": "online",
        "llm_engine": "online" if settings.GROQ_API_KEY else "not_configured",
        "checked_at": datetime.utcnow().isoformat(),
    }