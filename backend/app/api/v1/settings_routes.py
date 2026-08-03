from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.settings import SettingsUpdate

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("")
def get_settings(user: User = Depends(get_current_user)):
    return {
        "theme": user.theme,
        "language": user.language,
        "email": user.email,
        "phone": user.phone,
    }


@router.put("")
def update_settings(
    payload: SettingsUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if payload.theme:
        user.theme = payload.theme
    if payload.language:
        user.language = payload.language
    if payload.phone is not None:
        user.phone = payload.phone
    db.commit()
    return {"message": "Settings updated"}


@router.delete("/account")
def delete_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(user)
    db.commit()
    return {"message": "Account deleted"}
