

"""Profile page: view/update the logged-in user's own account details."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.schemas.user import UserOut, UserUpdate

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=UserOut)
def get_profile(current_user=Depends(get_current_user)):
    return current_user


@router.put("", response_model=UserOut)
def update_profile(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url

    db.commit()
    db.refresh(current_user)
    return current_user