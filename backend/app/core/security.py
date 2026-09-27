"""
Warp Ladger — Security Utilities
JWT encoding/decoding, Argon2id password hashing, token generation.
"""
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import settings

log = structlog.get_logger(__name__)

# ─── Argon2id Password Hasher ────────────────────────────────
_ph = PasswordHasher(
    time_cost=settings.ARGON2_TIME_COST,
    memory_cost=settings.ARGON2_MEMORY_COST,
    parallelism=settings.ARGON2_PARALLELISM,
)


def hash_password(plain: str) -> str:
    """Hash a plain-text password using Argon2id."""
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against an Argon2id hash.

    Returns True if correct, False otherwise. Never raises.
    """
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(hashed: str) -> bool:
    """Check if a hash needs to be upgraded to current Argon2 parameters."""
    return _ph.check_needs_rehash(hashed)


# ─── JWT Tokens ──────────────────────────────────────────────
def create_access_token(
    subject: str,
    *,
    extra: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a short-lived JWT access token."""
    now = datetime.now(UTC)
    expire = now + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: str,
    *,
    extra: dict[str, Any] | None = None,
) -> str:
    """Create a longer-lived JWT refresh token."""
    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "refresh",
        "jti": generate_token(32),  # unique token ID for revocation
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, *, expected_type: str = "access") -> dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != expected_type:
        raise JWTError(f"Invalid token type: expected {expected_type}")
    return payload


# ─── Random Tokens ───────────────────────────────────────────
def generate_token(nbytes: int = 32) -> str:
    """Generate a cryptographically secure URL-safe token."""
    return secrets.token_urlsafe(nbytes)


def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP for email verification / MFA."""
    return "".join([str(secrets.randbelow(10)) for _ in range(length)])


def hash_token(token: str) -> str:
    """Hash a token for database storage (so raw tokens are never stored)."""
    import hashlib

    return hashlib.sha256(token.encode()).hexdigest()
