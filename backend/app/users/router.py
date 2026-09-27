"""Warp Ladger — Users Router"""
import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter
from app.core.dependencies import CurrentUser, DBSession
from app.database.models import User
from sqlalchemy import select

router = APIRouter()


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None


@router.get("/me")
async def get_profile(current_user: CurrentUser):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "avatar_url": current_user.avatar_url,
        "email_verified": current_user.email_verified,
        "is_superadmin": current_user.is_superadmin,
        "locale": current_user.locale,
        "timezone": current_user.timezone,
    }


@router.patch("/me")
async def update_profile(
    body: UpdateProfileRequest, current_user: CurrentUser, db: DBSession
):
    if body.full_name is not None:
        current_user.full_name = body.full_name
    if body.locale is not None:
        current_user.locale = body.locale
    if body.timezone is not None:
        current_user.timezone = body.timezone
    await db.flush()
    return {"message": "Profile updated."}
