import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SettingsUpdate(BaseModel):
    theme: Optional[str] = None
    language: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class SessionResponse(BaseModel):
    id: uuid.UUID
    device: Optional[str]
    ip_address: Optional[str]
    is_current: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ActivityLogResponse(BaseModel):
    id: uuid.UUID
    action: str
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyCreate(BaseModel):
    name: str


class APIKeyCreatedResponse(BaseModel):
    id: uuid.UUID
    name: str
    key: str  # full key shown only once
    key_prefix: str


class APIKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
