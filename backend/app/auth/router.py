"""
Warp Ladger — Auth Router
Endpoints: register, login, logout, refresh, verify-email, forgot-password, reset-password, /me
"""
from typing import Optional

import structlog
from fastapi import APIRouter, Cookie, Depends, Request, Response

from app.auth.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.auth.service import AuthService
from app.core.config import settings
from app.core.dependencies import CurrentUser, DBSession
from app.core.email import EmailService
from app.core.exceptions import TokenInvalidError

log = structlog.get_logger(__name__)

router = APIRouter()

COOKIE_KWARGS = {
    "httponly": True,
    "samesite": "strict",
    "secure": settings.is_production,
}


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        "wl_access_token",
        access_token,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **COOKIE_KWARGS,
    )
    response.set_cookie(
        "wl_refresh_token",
        refresh_token,
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        **COOKIE_KWARGS,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("wl_access_token")
    response.delete_cookie("wl_refresh_token")


# ── POST /register ────────────────────────────────────────────
@router.post("/register", status_code=201, response_model=dict)
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    db: DBSession,
):
    """Register a new account. Sends a verification email."""
    service = AuthService(db)
    user, verify_token = await service.register(
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        ip_address=request.client.host if request.client else None,
    )
    email_svc = EmailService()
    await email_svc.send_verification_email(
        to_email=user.email,
        full_name=user.full_name,
        token=verify_token,
    )
    return {
        "message": "Registration successful. Please check your email to verify your account.",
        "user_id": str(user.id),
    }


# ── POST /login ───────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: DBSession,
):
    """Authenticate and receive tokens via HttpOnly cookies."""
    service = AuthService(db)
    device_hint = request.headers.get("User-Agent", "")[:255]
    access_token, refresh_token = await service.login(
        email=body.email,
        password=body.password,
        ip_address=request.client.host if request.client else None,
        device_hint=device_hint,
    )
    _set_auth_cookies(response, access_token, refresh_token)
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ── POST /refresh ─────────────────────────────────────────────
@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: DBSession,
    wl_refresh_token: Optional[str] = Cookie(default=None),
    body: Optional[RefreshTokenRequest] = None,
):
    """Rotate the refresh token and issue new tokens."""
    token = wl_refresh_token or (body.refresh_token if body else None)
    if not token:
        raise TokenInvalidError("No refresh token provided.")

    service = AuthService(db)
    device_hint = request.headers.get("User-Agent", "")[:255]
    access_token, new_refresh_token = await service.refresh_tokens(
        refresh_token=token,
        ip_address=request.client.host if request.client else None,
        device_hint=device_hint,
    )
    _set_auth_cookies(response, access_token, new_refresh_token)
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ── POST /logout ──────────────────────────────────────────────
@router.post("/logout", status_code=200)
async def logout(
    response: Response,
    current_user: CurrentUser,
    db: DBSession,
    wl_refresh_token: Optional[str] = Cookie(default=None),
):
    """Revoke the current session and clear cookies."""
    service = AuthService(db)
    await service.logout(refresh_token=wl_refresh_token, user_id=current_user.id)
    _clear_auth_cookies(response)
    return {"message": "Logged out successfully."}


# ── POST /verify-email ────────────────────────────────────────
@router.post("/verify-email", status_code=200)
async def verify_email(body: VerifyEmailRequest, db: DBSession):
    """Verify email address with the token received by email."""
    service = AuthService(db)
    user = await service.verify_email(token=body.token)
    return {"message": "Email verified successfully.", "user_id": str(user.id)}


# ── POST /forgot-password ─────────────────────────────────────
@router.post("/forgot-password", status_code=200)
async def forgot_password(body: ForgotPasswordRequest, db: DBSession):
    """Send a password reset email. Always returns 200 (no enumeration)."""
    service = AuthService(db)
    result = await service.send_password_reset(email=body.email)
    if result:
        user, reset_token = result
        email_svc = EmailService()
        await email_svc.send_password_reset_email(
            to_email=user.email,
            full_name=user.full_name,
            token=reset_token,
        )
    return {"message": "If an account with that email exists, a reset link has been sent."}


# ── POST /reset-password ──────────────────────────────────────
@router.post("/reset-password", status_code=200)
async def reset_password(body: ResetPasswordRequest, db: DBSession):
    """Apply a new password using the reset token."""
    service = AuthService(db)
    await service.reset_password(token=body.token, new_password=body.password)
    return {"message": "Password reset successfully. Please log in with your new password."}


# ── GET /me ───────────────────────────────────────────────────
@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser):
    """Return the currently authenticated user's profile."""
    return current_user
