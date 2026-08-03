import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_otp_code,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.activity_log import ActivityLog, LoginSession
from app.models.profile import UserProfile
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResendOTPRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserPublic,
    VerifyOTPRequest,
)
from app.services.email_service import email_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _issue_tokens(db: Session, user: User, request: Request) -> TokenResponse:
    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))

    session = LoginSession(
        user_id=user.id,
        device=request.headers.get("user-agent", "Unknown device")[:150],
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        refresh_token=refresh,
    )
    db.add(session)
    db.add(ActivityLog(user_id=user.id, action="User logged in", ip_address=session.ip_address))
    db.commit()
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        email_otp_code=create_otp_code(),
    )
    db.add(user)
    db.flush()
    db.add(UserProfile(user_id=user.id))
    db.commit()
    db.refresh(user)

    email_service.send_otp_email(user.email, user.email_otp_code)
    tokens = _issue_tokens(db, user, request)
    return AuthResponse(user=UserPublic.model_validate(user), tokens=tokens)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    tokens = _issue_tokens(db, user, request)
    return AuthResponse(user=UserPublic.model_validate(user), tokens=tokens)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    data = decode_token(payload.refresh_token)
    if not data or data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    session = (
        db.query(LoginSession)
        .filter(LoginSession.refresh_token == payload.refresh_token, LoginSession.is_active == True)  # noqa: E712
        .first()
    )
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or revoked")

    new_access = create_access_token(data["sub"])
    return TokenResponse(access_token=new_access, refresh_token=payload.refresh_token)


@router.post("/logout")
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    session = db.query(LoginSession).filter(LoginSession.refresh_token == payload.refresh_token).first()
    if session:
        session.is_active = False
        db.commit()
    return {"message": "Logged out successfully"}


@router.post("/logout-all")
def logout_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(LoginSession).filter(LoginSession.user_id == user.id).update({"is_active": False})
    db.add(ActivityLog(user_id=user.id, action="Logged out of all devices"))
    db.commit()
    return {"message": "Logged out of all devices"}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        reset_token = create_access_token(str(user.id))
        user.password_reset_token = reset_token
        db.commit()
        email_service.send_password_reset_email(user.email, reset_token)
    # Always return generic success to avoid leaking which emails exist
    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    data = decode_token(payload.token)
    if not data:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = db.get(User, data["sub"])
    if not user or user.password_reset_token != payload.token:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.hashed_password = hash_password(payload.new_password)
    user.password_reset_token = None
    db.add(ActivityLog(user_id=user.id, action="Password reset via email link"))
    db.commit()
    return {"message": "Password has been reset. You can now log in."}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.hashed_password = hash_password(payload.new_password)
    db.add(ActivityLog(user_id=user.id, action="Password changed"))
    db.commit()
    return {"message": "Password changed successfully"}


@router.post("/verify-otp")
def verify_otp(payload: VerifyOTPRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or user.email_otp_code != payload.otp_code:
        raise HTTPException(status_code=400, detail="Invalid OTP code")

    user.is_email_verified = True
    user.email_otp_code = None
    db.add(ActivityLog(user_id=user.id, action="Email verified via OTP"))
    db.commit()
    return {"message": "Email verified successfully"}


@router.post("/resend-otp")
def resend_otp(payload: ResendOTPRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user and not user.is_email_verified:
        user.email_otp_code = create_otp_code()
        db.commit()
        email_service.send_otp_email(user.email, user.email_otp_code)
    return {"message": "If that account exists, a new OTP has been sent."}


@router.get("/me", response_model=UserPublic)
def me(user: User = Depends(get_current_user)):
    return user
