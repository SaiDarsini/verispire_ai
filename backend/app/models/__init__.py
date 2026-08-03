"""
Import every model here so Base.metadata is fully populated
for Alembic autogeneration and for create_all() in dev.
"""
from app.models.user import User  # noqa
from app.models.profile import UserProfile, UserSkill  # noqa
from app.models.file import UserFile  # noqa
from app.models.notification import Notification  # noqa
from app.models.conversation import Conversation, Message  # noqa
from app.models.agent import Agent, UserAgent  # noqa
from app.models.task import Task  # noqa
from app.models.activity_log import ActivityLog, LoginSession  # noqa
from app.models.api_key import APIKey  # noqa
from app.models.integration import Integration  # noqa
from app.models.memory import MemoryItem  # noqa
