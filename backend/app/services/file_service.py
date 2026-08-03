"""
Handles saving uploaded files to disk under a per-user folder.
Swap the internals later for S3 / GCS without touching routers.
"""
import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings


class FileService:
    def __init__(self) -> None:
        self.base_dir = Path(settings.UPLOAD_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _user_dir(self, user_id: str) -> Path:
        d = self.base_dir / str(user_id)
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def save(self, user_id: str, upload: UploadFile, category: str = "general") -> dict:
        ext = os.path.splitext(upload.filename or "")[1]
        unique_name = f"{uuid.uuid4().hex}{ext}"
        dest = self._user_dir(user_id) / unique_name

        contents = await upload.read()
        max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
        if len(contents) > max_bytes:
            raise ValueError(f"File exceeds {settings.MAX_UPLOAD_MB}MB limit")

        with open(dest, "wb") as f:
            f.write(contents)

        return {
            "original_name": upload.filename or unique_name,
            "stored_path": str(dest),
            "content_type": upload.content_type or "application/octet-stream",
            "size_bytes": len(contents),
            "category": category,
        }

    def delete(self, stored_path: str) -> None:
        try:
            os.remove(stored_path)
        except FileNotFoundError:
            pass


file_service = FileService()
