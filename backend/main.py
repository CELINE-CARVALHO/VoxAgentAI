"""
VoxAgent AI backend entrypoint.
Run with: uvicorn app.main:app --reload --port 8000
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import init_db, SessionLocal
from app.routers import auth, dashboard, calls, knowledge, analytics, settings as settings_router, profile
from app.routers import voice
from app.routers import ws
from app.routers import audio_ws
# from app.routers import voice

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for VoxAgent AI — live AI voice call agent dashboard.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(calls.router)
app.include_router(knowledge.router)
app.include_router(analytics.router)
app.include_router(settings_router.router)
app.include_router(profile.router)
app.include_router(voice.router)
app.include_router(ws.router)
app.include_router(audio_ws.router)
# app.include_router(voice.router)


@app.on_event("startup")
def on_startup():
    # Dev convenience — creates tables if they don't exist yet.
    # In production, run `alembic upgrade head` instead and remove this call.
    init_db()


@app.get("/api/health", tags=["health"])
def health_check():
    db_status = "ok"
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception as exc:
        db_status = f"error: {exc}"

    overall_ok = db_status == "ok"

    return {
        "status": "ok" if overall_ok else "degraded",
        "service": settings.APP_NAME,
        "env": settings.ENV,
        "database": db_status,
        "llm_configured": bool(settings.GROQ_API_KEY),
    }