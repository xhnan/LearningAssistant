from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_active_user
from db.session import get_db
from models.user import User
from models.profile import UserProfile

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    learning_level: str | None = None
    learning_goals: str | None = None
    preferred_style: str | None = None
    known_background: str | None = None
    constraints: str | None = None


class ProfileResponse(BaseModel):
    learning_level: str | None
    learning_goals: str | None
    preferred_style: str | None
    known_background: str | None
    constraints: str | None

    model_config = {"from_attributes": True}


@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        return ProfileResponse(
            learning_level=None,
            learning_goals=None,
            preferred_style=None,
            known_background=None,
            constraints=None,
        )
    return profile


@router.put("", response_model=ProfileResponse)
async def upsert_profile(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = UserProfile(user_id=current_user.id, **body.model_dump())
        db.add(profile)
    else:
        for field, value in body.model_dump().items():
            if value is not None:
                setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return profile
