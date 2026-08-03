import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import hash_password
from app.db.session import get_db
from app.models.api_key import APIKey
from app.models.user import User
from app.schemas.settings import APIKeyCreate, APIKeyCreatedResponse, APIKeyResponse

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


@router.get("", response_model=list[APIKeyResponse])
def list_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(APIKey).filter(APIKey.user_id == user.id).order_by(APIKey.created_at.desc()).all()


@router.post("", response_model=APIKeyCreatedResponse, status_code=201)
def create_key(payload: APIKeyCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    raw_key = f"vic_{secrets.token_urlsafe(32)}"
    prefix = raw_key[:12]

    record = APIKey(
        user_id=user.id, name=payload.name, key_prefix=prefix, hashed_key=hash_password(raw_key)
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return APIKeyCreatedResponse(id=record.id, name=record.name, key=raw_key, key_prefix=prefix)


@router.delete("/{key_id}", status_code=204)
def revoke_key(key_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.query(APIKey).filter(APIKey.id == key_id, APIKey.user_id == user.id).first()
    if not record:
        raise HTTPException(status_code=404, detail="API key not found")
    db.delete(record)
    db.commit()
    return None
