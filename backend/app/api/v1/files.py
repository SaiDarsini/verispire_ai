from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.file import UserFile
from app.models.user import User
from app.schemas.file import FileRenameRequest, FileResponse
from app.services.file_service import file_service

TEXT_EXTENSIONS = (".txt", ".md", ".csv", ".json")

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("", response_model=list[FileResponse])
def list_files(
    search: Optional[str] = None,
    category: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(UserFile).filter(UserFile.user_id == user.id)
    if search:
        query = query.filter(UserFile.original_name.ilike(f"%{search}%"))
    if category:
        query = query.filter(UserFile.category == category)
    return query.order_by(UserFile.created_at.desc()).all()


@router.post("", response_model=FileResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    category: str = "general",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        saved = await file_service.save(str(user.id), file, category)
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e))

    record = UserFile(user_id=user.id, **saved)
    db.add(record)
    db.commit()
    db.refresh(record)

    # Best-effort: pull plain-text file content into Memory. PDFs/docx aren't
    # parsed yet — only plain text-based formats.
    if record.original_name.lower().endswith(TEXT_EXTENSIONS):
        try:
            from app.models.memory import MemoryItem
            with open(record.stored_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read(3000).strip()
            if text:
                db.add(MemoryItem(
                    user_id=user.id,
                    content=f"From uploaded file '{record.original_name}': {text[:1500]}",
                    source="file",
                    source_label=record.original_name,
                ))
                db.commit()
        except Exception:  # noqa: BLE001
            pass

    return record


@router.patch("/{file_id}", response_model=FileResponse)
def rename_file(
    file_id: str,
    payload: FileRenameRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(UserFile).filter(UserFile.id == file_id, UserFile.user_id == user.id).first()
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    record.original_name = payload.new_name
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{file_id}", status_code=204)
def delete_file(file_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.query(UserFile).filter(UserFile.id == file_id, UserFile.user_id == user.id).first()
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    file_service.delete(record.stored_path)
    db.delete(record)
    db.commit()
    return None
