"""
SQLAlchemy engine, session factory, and declarative Base.
Import `get_db` as a FastAPI dependency wherever a route needs DB access.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Create all tables. Fine for development; for production, prefer the
    Alembic migrations instead of calling this directly.
    """
    from backend.app.models.user import call, transcript, knowledge, user, setting  # noqa: F401
    Base.metadata.create_all(bind=engine)