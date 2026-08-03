from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.memory import MemoryItem
from app.models.user import User
from app.schemas.memory import MemoryCreate, MemoryResponse, MemoryUpdate

router = APIRouter(prefix="/memory", tags=["Memory"])


@router.get("", response_model=list[MemoryResponse])
def list_memory(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(MemoryItem)
        .filter(MemoryItem.user_id == user.id)
        .order_by(MemoryItem.created_at.desc())
        .all()
    )


@router.post("", response_model=MemoryResponse, status_code=201)
def create_memory(
    payload: MemoryCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    item = MemoryItem(user_id=user.id, content=payload.content, source="manual")
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{memory_id}", response_model=MemoryResponse)
def update_memory(
    memory_id: str,
    payload: MemoryUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(MemoryItem).filter(MemoryItem.id == memory_id, MemoryItem.user_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Memory item not found")
    item.content = payload.content
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{memory_id}", status_code=204)
def delete_memory(memory_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(MemoryItem).filter(MemoryItem.id == memory_id, MemoryItem.user_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Memory item not found")
    db.delete(item)
    db.commit()
    return None


def get_memory_context(db: Session, user_id) -> list[str]:
    """Used by conversations.py to inject saved memory into the AI's context."""
    items = (
        db.query(MemoryItem)
        .filter(MemoryItem.user_id == user_id)
        .order_by(MemoryItem.created_at.desc())
        .limit(20)
        .all()
    )
    return [i.content for i in items]