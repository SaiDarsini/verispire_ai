from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.models.memory import MemoryItem
from app.api.v1.memory import get_memory_context

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.conversation import Conversation, Message
from app.models.activity_log import ActivityLog
from app.models.profile import UserProfile
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetail,
    ConversationResponse,
    MessageCreate,
    MessageDispatch,
    MessageResponse,
)
from app.services.ai_service import ai_service
from app.services import build_service
from app.services.verifier_engine.orchestrator import OrchestratorEngine
from app.core.security import decode_token

router = APIRouter(prefix="/conversations", tags=["Conversations"])
optional_bearer = HTTPBearer(auto_error=False)
orchestrator = OrchestratorEngine()


def _guest_user(db: Session) -> User:
    user = db.query(User).filter(User.email == "guest@localhost").first()
    if user:
        return user
    user = User(
        full_name="Local Guest",
        email="guest@localhost",
        hashed_password="guest-local-only",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _optional_user(
    credentials: HTTPAuthorizationCredentials | None,
    db: Session,
) -> User:
    if credentials:
        payload = decode_token(credentials.credentials)
        if payload and payload.get("type") == "access":
            user = db.get(User, payload.get("sub"))
            if user and user.is_active:
                return user
    return _guest_user(db)


@router.get("", response_model=list[ConversationResponse])
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


@router.post("", response_model=ConversationResponse, status_code=201)
def create_conversation(
    payload: ConversationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    convo = Conversation(user_id=user.id, title=payload.title, agent_key=payload.agent_key)
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    convo = db.query(Conversation).filter(
        Conversation.id == conversation_id, Conversation.user_id == user.id
    ).first()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return convo


@router.post("/messages", status_code=status.HTTP_201_CREATED)
async def dispatch_message(
    payload: MessageDispatch,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    db: Session = Depends(get_db),
):
    """Dispatch one query through the verifier engine, with local guest fallback."""
    user = _optional_user(credentials, db)
    convo = None
    if payload.conversation_id:
        convo = db.query(Conversation).filter(
            Conversation.id == payload.conversation_id,
            Conversation.user_id == user.id,
        ).first()
        if not convo:
            raise HTTPException(status_code=404, detail="Conversation not found")
    if convo is None:
        convo = Conversation(
            user_id=user.id,
            title=payload.prompt[:80] or "Verification",
            agent_key=payload.agent_key,
        )
        db.add(convo)
        db.flush()

    history = [{"role": message.role, "content": message.content} for message in convo.messages]
    user_message = Message(conversation_id=convo.id, role="user", content=payload.prompt)
    db.add(user_message)
    result = await orchestrator.process_query(
        payload.prompt,
        agent_key=payload.agent_key,
        history=history,
    )
    assistant_message = Message(
        conversation_id=convo.id,
        role="assistant",
        content=result["content"],
    )
    db.add(assistant_message)
    audit = result["audit"]
    db.add(ActivityLog(
        user_id=user.id,
        action=(
            f"verification agent={payload.agent_key} status={audit['status']} "
            f"exit={audit['sandbox_exit_code']} latency_ms={audit['latency_ms']}"
        ),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    ))
    db.commit()
    db.refresh(assistant_message)
    return {
        "content": result["content"],
        "audit": audit,
        "conversation_id": str(convo.id),
        "message_id": str(assistant_message.id),
    }


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    convo = db.query(Conversation).filter(
        Conversation.id == conversation_id, Conversation.user_id == user.id
    ).first()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(convo)
    db.commit()
    return None


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
async def send_message(
    conversation_id: str,
    payload: MessageCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    convo = db.query(Conversation).filter(
        Conversation.id == conversation_id, Conversation.user_id == user.id
    ).first()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_msg = Message(conversation_id=convo.id, role="user", content=payload.content)
    db.add(user_msg)

    # Auto-title fresh conversations from the first message.
    if convo.title in ("New Conversation", ""):
        convo.title = await ai_service.generate_title(payload.content)

    history = [{"role": m.role, "content": m.content} for m in convo.messages]
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    user_context = {
        "occupation": profile.occupation if profile else None,
        "skills": [s.name for s in profile.skills] if profile else [],
        "memories": get_memory_context(db, user.id),
    }

    # --- THE ONLY LINE THAT CHANGES IN VERSION 2 ---
    ai_text = await ai_service.generate_response(
        message=payload.content,
        history=history,
        agent_key=convo.agent_key,
        user_context=user_context,
    )

    parsed_files = build_service.parse_files(ai_text)
    project = build_service.save_project(str(user.id), parsed_files, db) if parsed_files else None
    display_content = build_service.strip_file_blocks(ai_text) if parsed_files else ai_text
    if project:
        summary = f"Built this as a {project['file_count']}-file project — preview and download below."
        display_content = f"{display_content}\n\n{summary}".strip() if display_content else summary

    ai_msg = Message(
        conversation_id=convo.id,
        role="assistant",
        content=display_content,
        preview_url=project["preview_url"] if project else None,
        zip_url=project["zip_url"] if project else None,
    )
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)

    # Best-effort: never let memory extraction break the chat response.
    try:
        fact = await ai_service.extract_memory(payload.content, display_content)
        if fact:
            db.add(MemoryItem(user_id=user.id, content=fact, source="chat", source_label=convo.title))
            db.commit()
        if project:
            file_list = ", ".join(project["file_names"])
            db.add(MemoryItem(
                user_id=user.id,
                content=(
                    f"Generated a project via {convo.agent_key.title()} AI containing: "
                    f"{file_list}. Context: {payload.content[:200]}"
                ),
                source="file",
                source_label=f"Generated project {project['project_id'][:8]}",
            ))
            db.commit()
    except Exception:  # noqa: BLE001
        pass

    return ai_msg