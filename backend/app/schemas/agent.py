import uuid

from pydantic import BaseModel


class AgentResponse(BaseModel):
    id: uuid.UUID
    key: str
    name: str
    description: str
    icon: str
    category: str
    is_active: bool
    is_enabled: bool = True

    class Config:
        from_attributes = True


class AgentToggleRequest(BaseModel):
    agent_key: str
    is_enabled: bool
