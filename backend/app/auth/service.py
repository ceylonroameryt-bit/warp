"""
Warp Ladger — Auth Service
Registration, login, token management, email verification, password reset.
"""
import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    NotFoundError,
    TokenExpiredError,
    TokenInvalidError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_token,
    hash_password,
    hash_token,
    password_needs_rehash,
    verify_password,
)
from app.audit.service import AuditService
from app.database.models import AuthProvider, AuthProviderType, RefreshToken, User

log = structlog.get_logger(__name__)

# Token expiry constants
EMAIL_VERIFY_TOKEN_TTL_HOURS = 24
PASSWORD_RESET_TOKEN_TTL_HOURS = 2


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Registration ─────────────────────────────────────────
    async def register(
        self,
        *,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> tuple[User, str]:
        """
        Register a new user.
        Returns (user, email_verification_token).
        """
        email = email.lower().strip()

        # Check uniqueness
        existing = await self.db.execute(
            select(User).where(User.email == email).where(User.deleted_at.is_(None))
        )
        if existing.scalar_one_or_none():
            raise ConflictError("An account with this email address already exists.")

        # Determine if first user → superadmin
        user_count_result = await self.db.execute(select(User).limit(1))
        is_first_user = user_count_result.scalar_one_or_none() is None

        verify_token = generate_token(32)
        verify_token_hash = hash_token(verify_token)

        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            is_superadmin=is_first_user,
            email_verification_token_hash=verify_token_hash,
            email_verification_sent_at=datetime.now(UTC),
        )
        self.db.add(user)

        # Create local auth provider record
        auth_provider = AuthProvider(user=user, provider=AuthProviderType.local)
        self.db.add(auth_provider)

        await self.db.flush()

        await AuditService.log_static(
            self.db,
            action="auth.register",
            resource_type="user",
            resource_id=str(user.id),
            user_id=user.id,
            ip_address=ip_address,
            diff={"email": user.email, "full_name": user.full_name},
        )

        log.info(
            "user_registered",
            user_id=str(user.id),
            email=user.email,
            is_superadmin=user.is_superadmin,
        )

        return user, verify_token

    # ── Email Verification ────────────────────────────────────
    async def verify_email(self, *, token: str) -> User:
        """Mark the user's email as verified."""
        token_hash = hash_token(token)
        result = await self.db.execute(
            select(User)
            .where(User.email_verification_token_hash == token_hash)
            .where(User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise TokenInvalidError("Invalid verification link.")

        if user.email_verified:
            return user  # idempotent

        # Check expiry (24 hours)
        if user.email_verification_sent_at:
            expiry = user.email_verification_sent_at + timedelta(
                hours=EMAIL_VERIFY_TOKEN_TTL_HOURS
            )
            if datetime.now(UTC) > expiry:
                raise TokenExpiredError("This verification link has expired.")

        user.email_verified = True
        user.email_verification_token_hash = None
        await self.db.flush()

        await AuditService.log_static(
            self.db,
            action="auth.email_verified",
            resource_type="user",
            resource_id=str(user.id),
            user_id=user.id,
        )

        log.info("email_verified", user_id=str(user.id))
        return user

    # ── Login ────────────────────────────────────────────────
    async def login(
        self,
        *,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        device_hint: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Authenticate a user.
        Returns (access_token, refresh_token).
        Uses constant-time comparison to prevent timing attacks.
        """
        email = email.lower().strip()
        result = await self.db.execute(
            select(User)
            .where(User.email == email)
            .where(User.is_active.is_(True))
            .where(User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()

        # Always hash even on miss to prevent timing oracle
        _dummy_hash = "$argon2id$v=19$m=65536,t=2,p=2$dummy"
        if user is None:
            verify_password(password, _dummy_hash)
            raise InvalidCredentialsError()

        if not verify_password(password, user.hashed_password or _dummy_hash):
            log.warning("login_failed_bad_password", email=email)
            raise InvalidCredentialsError()

        if not user.email_verified:
            raise EmailNotVerifiedError()

        # Rehash if parameters changed
        if user.hashed_password and password_needs_rehash(user.hashed_password):
            user.hashed_password = hash_password(password)
            await self.db.flush()

        access_token, refresh_token = await self._issue_tokens(
            user=user, ip_address=ip_address, device_hint=device_hint
        )

        await AuditService.log_static(
            self.db,
            action="auth.login",
            resource_type="user",
            resource_id=str(user.id),
            user_id=user.id,
            ip_address=ip_address,
        )

        log.info("user_logged_in", user_id=str(user.id))
        return access_token, refresh_token

    # ── Token Refresh ─────────────────────────────────────────
    async def refresh_tokens(
        self,
        *,
        refresh_token: str,
        ip_address: Optional[str] = None,
        device_hint: Optional[str] = None,
    ) -> tuple[str, str]:
        """Rotate refresh token and issue new access + refresh tokens."""
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
            user_id_str: str = payload["sub"]
        except Exception:
            raise TokenInvalidError()

        token_hash = hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .where(RefreshToken.revoked_at.is_(None))
        )
        stored_token = result.scalar_one_or_none()

        if stored_token is None:
            # Possible token reuse attack — revoke all user tokens
            log.warning("refresh_token_reuse_detected", user_id=user_id_str)
            await self._revoke_all_user_tokens(uuid.UUID(user_id_str))
            raise TokenInvalidError("Token reuse detected. Please log in again.")

        if datetime.now(UTC) > stored_token.expires_at.replace(tzinfo=UTC):
            stored_token.revoked_at = datetime.now(UTC)
            await self.db.flush()
            raise TokenExpiredError()

        # Revoke the used token
        stored_token.revoked_at = datetime.now(UTC)
        await self.db.flush()

        user_result = await self.db.execute(
            select(User)
            .where(User.id == uuid.UUID(user_id_str))
            .where(User.is_active.is_(True))
            .where(User.deleted_at.is_(None))
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            raise TokenInvalidError()

        return await self._issue_tokens(user=user, ip_address=ip_address, device_hint=device_hint)

    # ── Logout ────────────────────────────────────────────────
    async def logout(self, *, refresh_token: Optional[str] = None, user_id: uuid.UUID) -> None:
        """Revoke the given refresh token (or all tokens if none given)."""
        if refresh_token:
            token_hash = hash_token(refresh_token)
            await self.db.execute(
                update(RefreshToken)
                .where(RefreshToken.token_hash == token_hash)
                .values(revoked_at=datetime.now(UTC))
            )
        else:
            await self._revoke_all_user_tokens(user_id)

        if user_id:
            await AuditService.log_static(
                self.db,
                action="auth.logout",
                resource_type="user",
                resource_id=str(user_id),
                user_id=user_id,
            )

    # ── Forgot Password ───────────────────────────────────────
    async def send_password_reset(self, *, email: str) -> Optional[tuple[User, str]]:
        """
        Initiate password reset. Always returns None to prevent email enumeration.
        Caller must check return value and send email if not None.
        """
        email = email.lower().strip()
        result = await self.db.execute(
            select(User)
            .where(User.email == email)
            .where(User.is_active.is_(True))
            .where(User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        if user is None:
            return None  # silently succeed — no enumeration

        reset_token = generate_token(32)
        user.password_reset_token_hash = hash_token(reset_token)
        user.password_reset_sent_at = datetime.now(UTC)
        await self.db.flush()

        log.info("password_reset_requested", user_id=str(user.id))
        return user, reset_token

    # ── Reset Password ────────────────────────────────────────
    async def reset_password(self, *, token: str, new_password: str) -> User:
        """Apply a password reset using the one-time token."""
        token_hash = hash_token(token)
        result = await self.db.execute(
            select(User)
            .where(User.password_reset_token_hash == token_hash)
            .where(User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise TokenInvalidError("Invalid or expired password reset link.")

        if user.password_reset_sent_at:
            expiry = user.password_reset_sent_at + timedelta(hours=PASSWORD_RESET_TOKEN_TTL_HOURS)
            if datetime.now(UTC) > expiry:
                raise TokenExpiredError("This password reset link has expired.")

        user.hashed_password = hash_password(new_password)
        user.password_reset_token_hash = None
        user.password_reset_sent_at = None

        # Revoke all sessions on password change (security best practice)
        await self._revoke_all_user_tokens(user.id)
        await self.db.flush()

        await AuditService.log_static(
            self.db,
            action="auth.password_reset",
            resource_type="user",
            resource_id=str(user.id),
            user_id=user.id,
        )

        log.info("password_reset_completed", user_id=str(user.id))
        return user

    # ── Private helpers ───────────────────────────────────────
    async def _issue_tokens(
        self,
        *,
        user: User,
        ip_address: Optional[str] = None,
        device_hint: Optional[str] = None,
    ) -> tuple[str, str]:
        """Create, store, and return (access_token, refresh_token)."""
        extra = {"email": user.email, "is_superadmin": user.is_superadmin}
        access_token = create_access_token(str(user.id), extra=extra)
        refresh_token = create_refresh_token(str(user.id))

        stored = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            ip_address=ip_address,
            device_hint=device_hint,
        )
        self.db.add(stored)
        await self.db.flush()

        return access_token, refresh_token

    async def _revoke_all_user_tokens(self, user_id: uuid.UUID) -> None:
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .where(RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
