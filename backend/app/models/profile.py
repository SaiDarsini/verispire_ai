import uuid

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDMixin


class UserProfile(UUIDMixin, TimestampMixin, Base):
    """Everything captured during onboarding + editable later in Profile page."""

    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )

    occupation: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Q1
    ai_interests: Mapped[list] = mapped_column(JSON, default=list)  # Q2 multi-select
    ai_familiarity: Mapped[str | None] = mapped_column(String(20), nullable=True)  # Q4
    resume_path: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Q5

    bio: Mapped[str | None] = mapped_column(String(500), nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String(50), nullable=True)

    user: Mapped["User"] = relationship(back_populates="profile")
    skills: Mapped[list["UserSkill"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class UserSkill(UUIDMixin, TimestampMixin, Base):
    """Normalized skill rows (Q3 autocomplete selections)."""

    __tablename__ = "user_skills"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)

    profile: Mapped["UserProfile"] = relationship(back_populates="skills")
