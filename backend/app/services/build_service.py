"""
Parses AI responses that contain multiple generated files (marked with
###FILE: path### blocks), saves them to disk under the user's upload
folder, zips them for download, and — since /uploads is already served
publicly — returns a live preview URL for free if an index.html exists.
"""
import re
import uuid
import zipfile
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.file import UserFile

FILE_BLOCK_RE = re.compile(
    r"###FILE:\s*(.+?)\s*###\n(.*?)(?=\n###FILE:|\n###END###|$)", re.DOTALL
)


def parse_files(ai_text: str) -> dict[str, str]:
    matches = FILE_BLOCK_RE.findall(ai_text)
    return {path.strip(): content.strip() for path, content in matches if path.strip()}


def strip_file_blocks(ai_text: str) -> str:
    return re.sub(r"###FILE:.*?(?:###END###|$)", "", ai_text, flags=re.DOTALL).strip()


def save_project(user_id: str, files: dict[str, str], db: Session) -> Optional[dict]:
    if not files:
        return None

    project_id = uuid.uuid4().hex
    base = Path(settings.UPLOAD_DIR) / str(user_id) / "generated" / project_id
    base.mkdir(parents=True, exist_ok=True)

    for rel_path, content in files.items():
        safe_path = rel_path.replace("..", "").lstrip("/\\")
        dest = base / safe_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(content)

    zip_dir = Path(settings.UPLOAD_DIR) / str(user_id) / "generated_zips"
    zip_dir.mkdir(parents=True, exist_ok=True)
    zip_path = zip_dir / f"{project_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel_path in files:
            safe_path = rel_path.replace("..", "").lstrip("/\\")
            zf.write(base / safe_path, arcname=safe_path)

    record = UserFile(
        user_id=user_id,
        original_name=f"project-{project_id[:8]}.zip",
        stored_path=str(zip_path),
        content_type="application/zip",
        size_bytes=zip_path.stat().st_size,
        category="generated_project",
    )
    db.add(record)
    db.commit()

    preview_url = None
    if "index.html" in files:
        preview_url = f"{settings.BACKEND_URL}/uploads/{user_id}/generated/{project_id}/index.html"

    zip_url = f"{settings.BACKEND_URL}/uploads/{user_id}/generated_zips/{project_id}.zip"

    return {
        "preview_url": preview_url,
        "zip_url": zip_url,
        "file_count": len(files),
        "project_id": project_id,
        "file_names": list(files.keys()),
    }