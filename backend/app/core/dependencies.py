"""
Warp Ladger — FastAPI Dependencies
Provides: current_user, require_org_member, require_permission
These are the core guards that enforce the full auth chain:
  Authenticated user → Org membership → Role → Permission → Resource
"""
import uuid
from typing import Annotated, Optional

import structlog
from fastapi import Cookie, Depends, Header, Path
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import (
    OrganisationMembershipError,
    PermissionDeniedError,
    TokenExpiredError,
    TokenInvalidError,
)
from app.core.security import decode_token
from app.database.base import get_db, get_redis
from app.database.models import Membership, MembershipStatus, Permission, Role, RolePermission, User

log = structlog.get_logger(__name__)


# ─── Database Session ─────────────────────────────────────────
DBSession = Annotated[AsyncSession, Depends(get_db)]


# ─── Authenticated User ───────────────────────────────────────
async def get_current_user(
    db: DBSession,
    access_token: Optional[str] = Cookie(default=None, alias="wl_access_token"),
    authorization: Optional[str] = Header(default=None),
) -> User:
    """
    Extract and validate the current user from either:
    - HttpOnly cookie (wl_access_token) — preferred
    - Authorization: Bearer <token> header — for API clients
    """
    token: Optional[str] = None

    if access_token:
        token = access_token
    elif authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

    if not token:
        raise TokenInvalidError("No authentication token provided.")

    try:
        payload = decode_token(token, expected_type="access")
        user_id_str: str = payload["sub"]
    except JWTError:
        raise TokenExpiredError()

    result = await db.execute(
        select(User)
        .where(User.id == uuid.UUID(user_id_str))
        .where(User.is_active.is_(True))
        .where(User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise TokenInvalidError("User account not found or is inactive.")

    structlog.contextvars.bind_contextvars(user_id=str(user.id), user_email=user.email)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_verified_user(current_user: CurrentUser) -> User:
    """Requires email verification in addition to authentication."""
    from app.core.exceptions import EmailNotVerifiedError

    if not current_user.email_verified:
        raise EmailNotVerifiedError()
    return current_user


VerifiedUser = Annotated[User, Depends(get_current_verified_user)]


# ─── Organisation Membership Guard ───────────────────────────
async def get_org_membership(
    org_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> Membership:
    """
    Validates that the current user is an active member of the given organisation.
    This is the first tenant isolation check.
    """
    result = await db.execute(
        select(Membership)
        .where(Membership.user_id == current_user.id)
        .where(Membership.organisation_id == org_id)
        .where(Membership.status == MembershipStatus.active)
        .options(selectinload(Membership.role).selectinload(Role.role_permissions))
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise OrganisationMembershipError()

    structlog.contextvars.bind_contextvars(org_id=str(org_id), role=membership.role.name)
    return membership


OrgMembership = Annotated[Membership, Depends(get_org_membership)]


# ─── Permission Guard Factory ────────────────────────────────
def require_permission(resource: str, action: str):
    """
    FastAPI dependency factory that checks a specific permission.

    Usage:
        @router.get("/...", dependencies=[Depends(require_permission("org", "update"))])
    """

    async def _check_permission(
        membership: OrgMembership,
        db: DBSession,
    ) -> None:
        # Superadmin bypass
        if membership.user.is_superadmin:
            return

        # Load permissions for this role
        result = await db.execute(
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == membership.role_id)
            .where(Permission.resource == resource)
            .where(Permission.action == action)
        )
        perm = result.scalar_one_or_none()
        if perm is None:
            raise PermissionDeniedError(
                f"Missing permission: {resource}:{action}"
            )

    return _check_permission


# ─── Superadmin Guard ─────────────────────────────────────────
async def require_superadmin(current_user: CurrentUser) -> User:
    """Only platform super-admins can access this endpoint."""
    if not current_user.is_superadmin:
        raise PermissionDeniedError("Platform admin access required.")
    return current_user


SuperAdmin = Annotated[User, Depends(require_superadmin)]


# ─── Optional User ────────────────────────────────────────────
async def get_optional_user(
    db: DBSession,
    access_token: Optional[str] = Cookie(default=None, alias="wl_access_token"),
    authorization: Optional[str] = Header(default=None),
) -> Optional[User]:
    """Returns the current user if authenticated, else None. Does not raise."""
    try:
        return await get_current_user(db, access_token, authorization)
    except Exception:
        return None


OptionalUser = Annotated[Optional[User], Depends(get_optional_user)]
