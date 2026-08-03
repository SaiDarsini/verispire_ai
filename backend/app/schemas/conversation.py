import uuid
from datetime import datetime
from typing import List
from typing import List, Optional

from pydantic import BaseModel


class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    preview_url: Optional[str] = None
    zip_url: Optional[str] = None

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    title: str = "New Conversation"
    agent_key: str = "personal"


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str
    agent_key: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationDetail(ConversationResponse):
    messages: List[MessageResponse] = []
