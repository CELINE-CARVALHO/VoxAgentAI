"""Settings page: per-account preferences (voice, default language, business hours, etc.)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.setting import Setting
from app.schemas.settings import SettingsOut, SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    row = db.query(Setting).filter(Setting.user_id == current_user.id).first()
    if not row:
        # Shouldn't normally happen (seeded at registration) — create a default on the fly.
        row = Setting(user_id=current_user.id, preferences={})
        db.add(row)
        db.commit()
        db.refresh(row)
    return SettingsOut(preferences=row.preferences)


@router.put("", response_model=SettingsOut)
def update_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    row = db.query(Setting).filter(Setting.user_id == current_user.id).first()
    if not row:
        row = Setting(user_id=current_user.id, preferences={})
        db.add(row)

    row.preferences = {**row.preferences, **payload.preferences}
    db.commit()
    db.refresh(row)
    return SettingsOut(preferences=row.preferences)