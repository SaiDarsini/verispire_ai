from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.agent import Agent, UserAgent
from app.models.user import User
from app.schemas.agent import AgentResponse, AgentToggleRequest

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("", response_model=list[AgentResponse])
def list_agents(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agents = db.query(Agent).filter(Agent.is_active == True).all()  # noqa: E712
    enabled_keys = {
        ua.agent_key
        for ua in db.query(UserAgent).filter(UserAgent.user_id == user.id, UserAgent.is_enabled == True).all()  # noqa: E712
    }
    # If the user has never toggled anything, everything defaults to enabled.
    has_any_pref = db.query(UserAgent).filter(UserAgent.user_id == user.id).count() > 0

    results = []
    for a in agents:
        is_enabled = (a.key in enabled_keys) if has_any_pref else True
        results.append(
            AgentResponse(
                id=a.id, key=a.key, name=a.name, description=a.description,
                icon=a.icon, category=a.category, is_active=a.is_active, is_enabled=is_enabled,
            )
        )
    return results


@router.post("/toggle")
def toggle_agent(
    payload: AgentToggleRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    record = db.query(UserAgent).filter(
        UserAgent.user_id == user.id, UserAgent.agent_key == payload.agent_key
    ).first()
    if record:
        record.is_enabled = payload.is_enabled
    else:
        db.add(UserAgent(user_id=user.id, agent_key=payload.agent_key, is_enabled=payload.is_enabled))
    db.commit()
    return {"message": "Agent preference updated"}
