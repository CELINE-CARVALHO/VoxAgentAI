"""
SQLAlchemy engine, session factory, and declarative Base.

This module centralizes database configuration for the entire backend.

Responsibilities:
- Create SQLAlchemy engine
- Create database sessions
- Provide FastAPI dependency (get_db)
- Initialize models during development
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# ------------------------------------------------------------------
# SQLAlchemy Engine
# ------------------------------------------------------------------

from sqlalchemy.pool import StaticPool

if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        future=True,
    )

# ------------------------------------------------------------------
# Session Factory
# ------------------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

# ------------------------------------------------------------------
# Declarative Base
# ------------------------------------------------------------------

Base = declarative_base()

# ------------------------------------------------------------------
# Dependency
# ------------------------------------------------------------------

def get_db():
    """
    FastAPI dependency.

    Example:

        @router.get("/")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------------------------------------------
# Database Initialization
# ------------------------------------------------------------------

def init_db():
    """
    Development helper.

    Imports every SQLAlchemy model so metadata is populated before
    calling create_all().

    NOTE:
        Production deployments should use Alembic migrations instead of
        create_all().
    """

    # Import models ONLY for metadata registration.
    from app.models.user import User
    from app.models.call import Call
    from app.models.transcript import Transcript
    from app.models.knowledge import KnowledgeDocument
    from app.models.setting import Setting

    # Prevent "unused import" removal
    _ = (User, Call, Transcript, KnowledgeDocument, Setting)

    Base.metadata.create_all(bind=engine)