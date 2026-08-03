import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MemoryCreate(BaseModel):
    content: str


class MemoryUpdate(BaseModel):
    content: str


class MemoryResponse(BaseModel):
    id: uuid.UUID
    content: str
    source: str
    source_label: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True