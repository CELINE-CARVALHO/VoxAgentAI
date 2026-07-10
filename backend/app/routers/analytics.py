"""
Analytics page: call volume over time, language breakdown, sentiment trends,
and latency/duration performance — matches the endpoints the frontend already
expects (see analytics.html's Dependencies comment):
  GET /api/analytics/calls?range=daily|weekly|monthly
  GET /api/analytics/languages
  GET /api/analytics/sentiment
  GET /api/analytics/performance
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.call import Call
from app.schemas.analytics import (
    CallVolumeOut, TimeseriesPoint, LanguageBreakdownOut,
    SentimentTrendOut, PerformanceOut,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

RANGE_CONFIG = {
    "daily": {"trunc": "day", "lookback": timedelta(days=7), "label_fmt": "%a"},
    "weekly": {"trunc": "week", "lookback": timedelta(weeks=8), "label_fmt": "Wk %U"},
    "monthly": {"trunc": "month", "lookback": timedelta(days=365), "label_fmt": "%b"},
}


from datetime import datetime

def format_bucket(bucket, fmt):
    # SQLite returns string
    if isinstance(bucket, str):
        try:
            if len(bucket) == 10:      # YYYY-MM-DD
                dt = datetime.strptime(bucket, "%Y-%m-%d")
            elif len(bucket) == 7:     # YYYY-MM
                dt = datetime.strptime(bucket, "%Y-%m")
            else:                      # YYYY-WW
                dt = datetime.strptime(bucket + "-1", "%Y-%W-%w")

            return dt.strftime(fmt)
        except Exception:
            return bucket

    # PostgreSQL returns datetime
    return bucket.strftime(fmt)


from app.config import settings

def get_bucket(column, range_type):

    if settings.DATABASE_URL.startswith("sqlite"):

        if range_type == "daily":
            return func.strftime("%Y-%m-%d", column)

        if range_type == "weekly":
            return func.strftime("%Y-%W", column)

        if range_type == "monthly":
            return func.strftime("%Y-%m", column)

    if range_type == "daily":
        return func.date_trunc("day", column)

    if range_type == "weekly":
        return func.date_trunc("week", column)

    if range_type == "monthly":
        return func.date_trunc("month", column)


def _validate_range(range: str) -> dict:
    return RANGE_CONFIG.get(range, RANGE_CONFIG["daily"])


@router.get("/calls", response_model=CallVolumeOut)
def call_volume(
    range: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    cfg = _validate_range(range)
    since = datetime.utcnow() - cfg["lookback"]

    bucket = get_bucket(Call.started_at, range)
    rows = (
        db.query(bucket.label("bucket"), func.count(Call.id).label("count"))
        .filter(Call.started_at >= since)
        .group_by(bucket)
        .order_by(bucket)
        .all()
    )

    points = [
        TimeseriesPoint(label=row.bucket, value=row.count)
        for row in rows
    ]
    return CallVolumeOut(range=range, points=points)


@router.get("/languages", response_model=list[LanguageBreakdownOut])
def language_breakdown(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = (
        db.query(Call.language, func.count(Call.id).label("count"))
        .filter(Call.language.isnot(None))
        .group_by(Call.language)
        .order_by(func.count(Call.id).desc())
        .all()
    )
    total = sum(r.count for r in rows) or 1
    return [
        LanguageBreakdownOut(language=r.language, count=r.count, percent=round(r.count / total * 100, 1))
        for r in rows
    ]


@router.get("/sentiment", response_model=SentimentTrendOut)
def sentiment_trend(
    range: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    cfg = _validate_range(range)
    since = datetime.utcnow() - cfg["lookback"]
    bucket = get_bucket(Call.started_at, range)

    rows = (
        db.query(
            bucket.label("bucket"),
            func.sum(case((Call.sentiment == "positive", 1), else_=0)).label("positive"),
            func.sum(case((Call.sentiment == "neutral", 1), else_=0)).label("neutral"),
            func.sum(case((Call.sentiment == "negative", 1), else_=0)).label("negative"),
        )
        .filter(Call.started_at >= since)
        .group_by(bucket)
        .order_by(bucket)
        .all()
    )

    return SentimentTrendOut(
        range=range,
        positive=[
            TimeseriesPoint(
                label=format_bucket(r.bucket, cfg["label_fmt"]),
                value=r.positive or 0,
            )
            for r in rows
        ],
        neutral=[
            TimeseriesPoint(
                label=format_bucket(r.bucket, cfg["label_fmt"]),
                value=r.neutral or 0,
            )
            for r in rows
        ],
        negative=[
            TimeseriesPoint(
                label=format_bucket(r.bucket, cfg["label_fmt"]),
                value=r.negative or 0,
            )
            for r in rows
        ],
    )


@router.get("/performance", response_model=PerformanceOut)
def performance(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    total_calls = db.query(func.count(Call.id)).scalar() or 0
    avg_latency = db.query(func.avg(Call.avg_latency_ms)).filter(Call.avg_latency_ms.isnot(None)).scalar() or 0
    avg_duration = db.query(func.avg(Call.duration_seconds)).filter(Call.duration_seconds.isnot(None)).scalar() or 0
    completed = db.query(func.count(Call.id)).filter(Call.status == "completed").scalar() or 0

    resolution_rate = round((completed / total_calls) * 100, 1) if total_calls else 0.0

    return PerformanceOut(
        avg_latency_ms=round(float(avg_latency), 1),
        avg_duration_seconds=round(float(avg_duration), 1),
        total_calls=total_calls,
        resolution_rate=resolution_rate,
    )

@router.get("/intents")
def top_intents(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return the most common intents detected across completed calls.
    """

    rows = (
        db.query(
            Call.intent.label("intent"),
            func.count(Call.id).label("count"),
            func.avg(Call.duration_seconds).label("avg_duration"),
        )
        .filter(Call.intent.isnot(None))
        .group_by(Call.intent)
        .order_by(desc("count"))
        .limit(limit)
        .all()
    )

    results = []

    for row in rows:

        sentiment = (
            db.query(Call.sentiment)
            .filter(Call.intent == row.intent)
            .filter(Call.sentiment.isnot(None))
            .first()
        )

        results.append(
            {
                "intent": row.intent,
                "count": row.count,
                "avg_sentiment": sentiment[0] if sentiment else "neutral",
                "avg_duration": round(row.avg_duration or 0),
            }
        )

    return results

