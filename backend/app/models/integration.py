import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin, UUIDMixin


class Integration(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "integrations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    provider: Mapped[str] = mapped_column(String(50))  # e.g. slack, github, notion
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    connected_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
