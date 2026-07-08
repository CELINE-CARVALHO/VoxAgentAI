"""
VoxAgent AI backend entrypoint.
Run with: uvicorn app.main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import auth, dashboard, calls, knowledge, analytics, settings as settings_router, profile

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


@app.on_event("startup")
def on_startup():
    # Dev convenience — creates tables if they don't exist yet.
    # In production, run `alembic upgrade head` instead and remove this call.
    init_db()


@app.get("/api/health", tags=["health"])
def health_check():
    return {"status": "ok", "service": settings.APP_NAME}