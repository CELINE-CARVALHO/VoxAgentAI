from sqlalchemy.orm import Session

from app.models.user import User
from app.models.setting import Setting
from app.schemas.user import UserCreate
from app.services.security import hash_password


def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, payload: UserCreate) -> User:
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Seed default settings row so GET /api/settings never 404s for a new user
    db.add(Setting(user_id=user.id, preferences={
        "voice": "alloy",
        "default_language": "en",
        "business_hours": "09:00-18:00",
        "escalation_email": "",
        "notifications_enabled": True,
    }))
    db.commit()

    return user