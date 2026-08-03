from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.activity_log import ActivityLog, LoginSession
from app.models.user import User
from app.schemas.settings import ActivityLogResponse, SessionResponse

router = APIRouter(prefix="/security", tags=["Security"])


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(LoginSession)
        .filter(LoginSession.user_id == user.id, LoginSession.is_active == True)  # noqa: E712
        .order_by(LoginSession.created_at.desc())
        .all()
    )


@router.delete("/sessions/{session_id}")
def revoke_session(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.query(LoginSession).filter(
        LoginSession.id == session_id, LoginSession.user_id == user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.is_active = False
    db.commit()
    return {"message": "Session revoked"}


@router.get("/activity-logs", response_model=list[ActivityLogResponse])
def activity_logs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(ActivityLog)
        .filter(ActivityLog.user_id == user.id)
        .order_by(ActivityLog.created_at.desc())
        .limit(100)
        .all()
    )
