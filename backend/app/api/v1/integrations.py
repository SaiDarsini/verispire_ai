from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.integration import Integration
from app.models.user import User

router = APIRouter(prefix="/integrations", tags=["Integrations"])

AVAILABLE_PROVIDERS = [
    {"provider": "slack", "name": "Slack", "description": "Send AI notifications to Slack channels."},
    {"provider": "github", "name": "GitHub", "description": "Let Developer AI read and open pull requests."},
    {"provider": "notion", "name": "Notion", "description": "Sync tasks and notes with Notion pages."},
    {"provider": "google_drive", "name": "Google Drive", "description": "Import and export files directly."},
    {"provider": "gmail", "name": "Gmail", "description": "Draft and send emails via your AI assistant."},
    {"provider": "stripe", "name": "Stripe", "description": "Let Finance AI track invoices and payments."},
]


@router.get("")
def list_integrations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    connected = {
        i.provider: i for i in db.query(Integration).filter(Integration.user_id == user.id).all()
    }
    result = []
    for p in AVAILABLE_PROVIDERS:
        record = connected.get(p["provider"])
        result.append(
            {
                **p,
                "is_connected": record.is_connected if record else False,
                "connected_email": record.connected_email if record else None,
            }
        )
    return result


@router.post("/{provider}/toggle")
def toggle_integration(provider: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.query(Integration).filter(
        Integration.user_id == user.id, Integration.provider == provider
    ).first()
    if not record:
        record = Integration(user_id=user.id, provider=provider, is_connected=True)
        db.add(record)
    else:
        record.is_connected = not record.is_connected
    db.commit()
    return {"provider": provider, "is_connected": record.is_connected}
