"""
Warp Ladger — Auth Schemas (Pydantic v2)
"""
import re
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=255)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        errors = []
        if not re.search(r"[A-Z]", v):
            errors.append("at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            errors.append("at least one lowercase letter")
        if not re.search(r"\d", v):
            errors.append("at least one digit")
        if not re.search(r"[^a-zA-Z0-9]", v):
            errors.append("at least one special character")
        if errors:
            raise ValueError(f"Password must contain: {', '.join(errors)}")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class TokenResponse(BaseModel):
    """Response after successful authentication."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    email_verified: bool
    is_superadmin: bool
    locale: str
    timezone: str

    model_config = {"from_attributes": True}


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        return RegisterRequest.validate_password_strength(v)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        return RegisterRequest.validate_password_strength(v)


class RefreshTokenRequest(BaseModel):
    """Used by API clients (cookie-based clients don't need this)."""
    refresh_token: Optional[str] = None
