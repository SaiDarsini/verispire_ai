from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.profile import UserProfile, UserSkill
from app.models.user import User
from app.schemas.profile import OnboardingComplete, ProfileResponse
from app.services.file_service import file_service

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

# Small in-memory catalog powering the Q3 skill autocomplete.
SKILL_CATALOG = [
    "HTML", "CSS", "JavaScript", "TypeScript", "Python", "Java", "C++", "C#",
    "React", "Vue", "Angular", "Node.js", "FastAPI", "Django", "Flask",
    "PostgreSQL", "MongoDB", "MySQL", "Docker", "Kubernetes", "AWS", "Azure",
    "Google Cloud", "Git", "Figma", "UI Design", "UX Research", "SEO",
    "Content Writing", "Copywriting", "Digital Marketing", "Social Media",
    "Data Analysis", "Machine Learning", "SQL", "Excel", "Project Management",
    "Sales", "Negotiation", "Public Speaking", "Photoshop", "Illustrator",
]


@router.get("/skills/autocomplete")
def autocomplete_skills(q: str = ""):
    q = q.strip().lower()
    if not q:
        return []
    matches = [s for s in SKILL_CATALOG if s.lower().startswith(q)]
    return matches[:10]


@router.post("/complete", response_model=ProfileResponse)
def complete_onboarding(
    payload: OnboardingComplete,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        db.flush()

    profile.occupation = payload.occupation
    profile.ai_interests = payload.ai_interests
    profile.ai_familiarity = payload.ai_familiarity
    profile.bio = payload.bio

    db.query(UserSkill).filter(UserSkill.profile_id == profile.id).delete()
    for skill_name in payload.skills:
        db.add(UserSkill(profile_id=profile.id, name=skill_name))

    user.has_completed_onboarding = True
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


@router.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    saved = await file_service.save(str(user.id), file, category="resume")
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    profile.resume_path = saved["stored_path"]
    db.commit()
    return {"message": "Resume uploaded", "path": saved["stored_path"]}


@router.get("/status")
def onboarding_status(user: User = Depends(get_current_user)):
    return {"has_completed_onboarding": user.has_completed_onboarding}
