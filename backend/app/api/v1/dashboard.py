from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.conversation import Conversation, Message
from app.models.file import UserFile
from app.models.notification import Notification
from app.models.task import Task
from app.models.user import User
from app.models.agent import Agent
from app.models.profile import UserProfile

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview")
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total_conversations = db.query(Conversation).filter(Conversation.user_id == user.id).count()
    total_messages = (
        db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.user_id == user.id)
        .count()
    )
    total_tasks = db.query(Task).filter(Task.user_id == user.id).count()
    tasks_done = db.query(Task).filter(Task.user_id == user.id, Task.status == "done").count()
    total_files = db.query(UserFile).filter(UserFile.user_id == user.id).count()
    unread_notifications = (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.is_read == False)  # noqa: E712
        .count()
    )

    return {
        "full_name": user.full_name,
        "stats": {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "total_tasks": total_tasks,
            "tasks_done": tasks_done,
            "total_files": total_files,
            "unread_notifications": unread_notifications,
        },
        "recent_conversations": [
            {"id": str(c.id), "title": c.title, "updated_at": c.updated_at.isoformat()}
            for c in db.query(Conversation)
            .filter(Conversation.user_id == user.id)
            .order_by(Conversation.updated_at.desc())
            .limit(5)
            .all()
        ],
    }


@router.get("/analytics")
def analytics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tasks_by_status = {}
    for status_key in ["todo", "in_progress", "done"]:
        tasks_by_status[status_key] = (
            db.query(Task).filter(Task.user_id == user.id, Task.status == status_key).count()
        )

    conversations_by_agent = {}
    for row in db.query(Conversation.agent_key, Conversation.id).filter(Conversation.user_id == user.id):
        conversations_by_agent[row.agent_key] = conversations_by_agent.get(row.agent_key, 0) + 1

    return {
        "tasks_by_status": tasks_by_status,
        "conversations_by_agent": conversations_by_agent,
    }

AGENT_KEYWORDS = {
    "developer": ["software", "developer", "engineer", "programmer", "coding", "code",
                  "python", "javascript", "backend", "frontend", "fullstack", "devops",
                  "web development", "app development", "data engineer"],
    "marketing": ["marketing", "growth", "seo", "content", "social media", "brand",
                  "advertising", "copywriting", "campaign"],
    "design": ["design", "ui", "ux", "graphic", "product design", "illustrator",
               "figma", "visual"],
    "research": ["research", "analyst", "data scientist", "scientist", "academic",
                 "phd", "data analysis"],
    "finance": ["finance", "accountant", "accounting", "investment", "banking",
                "financial analyst", "budget"],
    "hr": ["hr", "human resources", "recruiter", "talent", "people ops", "hiring"],
    "legal": ["legal", "lawyer", "attorney", "paralegal", "compliance", "contract"],
    "personal": [],
}

AGENT_STARTER_PROMPTS = {
    "developer": "Help me review this piece of code for bugs and best practices.",
    "marketing": "Draft a launch campaign plan for a new product.",
    "design": "Give me feedback on this UI layout and suggest improvements.",
    "research": "Research the latest trends in [topic] and summarize the findings.",
    "finance": "Help me build a simple monthly budget forecast.",
    "hr": "Draft a job description for a role I'm hiring for.",
    "legal": "Review this contract clause and flag anything risky.",
    "personal": "Help me plan and prioritize my week.",
}


@router.get("/recommendations")
def recommendations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    agents = db.query(Agent).filter(Agent.is_active == True).all()  # noqa: E712

    occupation = (profile.occupation or "").lower() if profile else ""
    skills = [s.name.lower() for s in profile.skills] if profile else []
    interests = [str(i).lower() for i in (profile.ai_interests or [])] if profile else []
    signal_text = " ".join([occupation] + skills + interests)

    scored = []
    for agent in agents:
        keywords = AGENT_KEYWORDS.get(agent.key, [])
        score = sum(1 for kw in keywords if kw in signal_text)
        if agent.key == "personal":
            score += 0.5
        scored.append((score, agent))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [a for score, a in scored if score > 0][:3]
    if not top:
        fallback_keys = ["personal", "research", "developer"]
        top = [a for a in agents if a.key in fallback_keys]

    return [
        {
            "agent_key": a.key,
            "name": a.name,
            "description": a.description,
            "icon": a.icon,
            "reason": f"Matches your background in {occupation}" if occupation else "A good starting point",
            "suggested_prompt": AGENT_STARTER_PROMPTS.get(a.key, "Say hello and see what I can help with."),
        }
        for a in top
    ]


