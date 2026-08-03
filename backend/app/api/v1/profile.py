from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.profile import UserProfile, UserSkill
from app.models.user import User
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.services.file_service import file_service

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    return ProfileResponse(
        id=profile.id,
        occupation=profile.occupation,
        ai_interests=profile.ai_interests,
        ai_familiarity=profile.ai_familiarity,
        resume_path=profile.resume_path,
        bio=profile.bio,
        skills=[s.name for s in profile.skills],
    )


@router.put("/me", response_model=ProfileResponse)
def update_my_profile(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()

    if payload.full_name:
        user.full_name = payload.full_name
    if payload.phone:
        user.phone = payload.phone
    if payload.bio is not None:
        profile.bio = payload.bio
    if payload.occupation is not None:
        profile.occupation = payload.occupation
    if payload.ai_interests is not None:
        profile.ai_interests = payload.ai_interests
    if payload.ai_familiarity is not None:
        profile.ai_familiarity = payload.ai_familiarity
    if payload.skills is not None:
        db.query(UserSkill).filter(UserSkill.profile_id == profile.id).delete()
        for skill_name in payload.skills:
            db.add(UserSkill(profile_id=profile.id, name=skill_name))

    db.commit()
    db.refresh(profile)
    return ProfileResponse(
        id=profile.id,
        occupation=profile.occupation,
        ai_interests=profile.ai_interests,
        ai_familiarity=profile.ai_familiarity,
        resume_path=profile.resume_path,
        bio=profile.bio,
        skills=[s.name for s in profile.skills],
    )


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    saved = await file_service.save(str(user.id), file, category="avatar")
    user.avatar_url = f"/api/v1/files/raw/{saved['stored_path']}"
    db.commit()
    return {"message": "Avatar updated", "avatar_url": user.avatar_url}
