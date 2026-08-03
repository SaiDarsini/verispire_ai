import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin, UUIDMixin


class MemoryItem(UUIDMixin, TimestampMixin, Base):
    """A durable fact the AI (or the user) has saved about the user.
    source: 'manual' (typed in Memory page), 'chat' (auto-extracted from a
    conversation), or 'file' (auto-extracted from an uploaded text file).
    """

    __tablename__ = "memory_items"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20), default="manual")
    source_label: Mapped[str | None] = mapped_column(String(255), nullable=True)