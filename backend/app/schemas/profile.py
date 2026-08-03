import uuid
from typing import List, Optional

from pydantic import BaseModel


class OnboardingStepOne(BaseModel):
    occupation: str


class OnboardingStepTwo(BaseModel):
    ai_interests: List[str]


class OnboardingStepThree(BaseModel):
    skills: List[str]


class OnboardingStepFour(BaseModel):
    ai_familiarity: str


class OnboardingComplete(BaseModel):
    occupation: str
    ai_interests: List[str]
    skills: List[str]
    ai_familiarity: str
    bio: Optional[str] = None


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    occupation: Optional[str] = None
    ai_interests: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    ai_familiarity: Optional[str] = None
    phone: Optional[str] = None


class ProfileResponse(BaseModel):
    id: uuid.UUID
    occupation: Optional[str]
    ai_interests: List[str]
    ai_familiarity: Optional[str]
    resume_path: Optional[str]
    bio: Optional[str]
    skills: List[str]

    class Config:
        from_attributes = True
