import uuid
from datetime import datetime

from pydantic import BaseModel


class FileResponse(BaseModel):
    id: uuid.UUID
    original_name: str
    content_type: str
    size_bytes: int
    category: str
    created_at: datetime

    class Config:
        from_attributes = True


class FileRenameRequest(BaseModel):
    new_name: str
