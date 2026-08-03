"""
Run once (python -m app.seed) to populate the AI agent catalog.
Safe to re-run: it upserts by `key`.
"""
from app.db.session import SessionLocal
from app.models.agent import Agent

AGENTS = [
    {"key": "developer", "name": "Developer AI", "description": "Writes, reviews, and debugs code across your stack.", "icon": "code", "category": "engineering"},
    {"key": "marketing", "name": "Marketing AI", "description": "Plans campaigns, writes copy, and analyzes growth.", "icon": "megaphone", "category": "growth"},
    {"key": "design", "name": "Design AI", "description": "Generates UI concepts, layouts, and design feedback.", "icon": "palette", "category": "design"},
    {"key": "research", "name": "Research AI", "description": "Digs through data and sources to answer deep questions.", "icon": "search", "category": "research"},
    {"key": "finance", "name": "Finance AI", "description": "Tracks spend, forecasts, and financial summaries.", "icon": "wallet", "category": "finance"},
    {"key": "hr", "name": "HR AI", "description": "Helps with hiring, onboarding docs, and policies.", "icon": "users", "category": "people"},
    {"key": "legal", "name": "Legal AI", "description": "Drafts and reviews contracts and legal checklists.", "icon": "scale", "category": "legal"},
    {"key": "personal", "name": "Personal AI", "description": "Your everyday assistant for anything on your mind.", "icon": "sparkles", "category": "general"},
]


def run():
    db = SessionLocal()
    try:
        for a in AGENTS:
            existing = db.query(Agent).filter(Agent.key == a["key"]).first()
            if existing:
                for k, v in a.items():
                    setattr(existing, k, v)
            else:
                db.add(Agent(**a))
        db.commit()
        print(f"Seeded {len(AGENTS)} agents.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
