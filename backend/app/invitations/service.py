"""Warp Ladger — Invitations Service"""
import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, InvitationError, NotFoundError
from app.core.security import generate_token, hash_token
from app.database.models import (
    Invitation,
    InvitationStatus,
    Membership,
    MembershipStatus,
    User,
)

log = structlog.get_logger(__name__)

INVITATION_TTL_DAYS = 7


class InvitationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_invitation(
        self,
        *,
        org_id: uuid.UUID,
        inviter_id: uuid.UUID,
        email: str,
        role_id: uuid.UUID,
    ) -> tuple[Invitation, str]:
        """Create an invitation. Returns (invitation, raw_token)."""
        email = email.lower().strip()

        # Check for existing active member
        user_result = await self.db.execute(
            select(User).where(User.email == email).where(User.deleted_at.is_(None))
        )
        existing_user = user_result.scalar_one_or_none()
        if existing_user:
            membership_result = await self.db.execute(
                select(Membership)
                .where(Membership.user_id == existing_user.id)
                .where(Membership.organisation_id == org_id)
                .where(Membership.status == MembershipStatus.active)
            )
            if membership_result.scalar_one_or_none():
                raise ConflictError("This user is already a member of the organisation.")

        # Cancel any existing pending invitations for the same email + org
        existing_invite_result = await self.db.execute(
            select(Invitation)
            .where(Invitation.organisation_id == org_id)
            .where(Invitation.email == email)
            .where(Invitation.status == InvitationStatus.pending)
        )
        for old_invite in existing_invite_result.scalars().all():
            old_invite.status = InvitationStatus.cancelled

        raw_token = generate_token(32)
        invitation = Invitation(
            organisation_id=org_id,
            inviter_id=inviter_id,
            email=email,
            role_id=role_id,
            token_hash=hash_token(raw_token),
            status=InvitationStatus.pending,
            expires_at=datetime.now(UTC) + timedelta(days=INVITATION_TTL_DAYS),
        )
        self.db.add(invitation)
        await self.db.flush()

        log.info("invitation_created", org_id=str(org_id), email=email)
        return invitation, raw_token

    async def accept_invitation(
        self,
        *,
        token: str,
        accepting_user_id: Optional[uuid.UUID] = None,
        accepting_email: Optional[str] = None,
    ) -> Invitation:
        """Accept an invitation. Creates membership."""
        token_hash = hash_token(token)
        result = await self.db.execute(
            select(Invitation).where(Invitation.token_hash == token_hash)
        )
        invitation = result.scalar_one_or_none()

        if invitation is None or invitation.status != InvitationStatus.pending:
            raise InvitationError("This invitation is invalid or has already been used.")

        if datetime.now(UTC) > invitation.expires_at.replace(tzinfo=UTC):
            invitation.status = InvitationStatus.expired
            raise InvitationError("This invitation has expired.")

        # Verify the accepting user's email matches the invitation
        if accepting_email and invitation.email.lower() != accepting_email.lower():
            raise InvitationError(
                "This invitation was sent to a different email address."
            )

        # Get or find user
        user_id = accepting_user_id
        if user_id is None:
            user_result = await self.db.execute(
                select(User)
                .where(User.email == invitation.email)
                .where(User.deleted_at.is_(None))
            )
            user = user_result.scalar_one_or_none()
            if user is None:
                raise InvitationError("No account found for this invitation email.")
            user_id = user.id

        membership = Membership(
            user_id=user_id,
            organisation_id=invitation.organisation_id,
            role_id=invitation.role_id,
            status=MembershipStatus.active,
            joined_at=datetime.now(UTC),
        )
        self.db.add(membership)

        invitation.status = InvitationStatus.accepted
        invitation.accepted_at = datetime.now(UTC)
        await self.db.flush()

        log.info("invitation_accepted", invitation_id=str(invitation.id), user_id=str(user_id))
        return invitation

    async def cancel_invitation(self, *, invitation_id: uuid.UUID, org_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(Invitation)
            .where(Invitation.id == invitation_id)
            .where(Invitation.organisation_id == org_id)
        )
        invitation = result.scalar_one_or_none()
        if invitation is None:
            raise NotFoundError("Invitation not found.")
        invitation.status = InvitationStatus.cancelled

    async def list_pending(self, org_id: uuid.UUID) -> list[Invitation]:
        result = await self.db.execute(
            select(Invitation)
            .where(Invitation.organisation_id == org_id)
            .where(Invitation.status == InvitationStatus.pending)
            .order_by(Invitation.created_at.desc())
        )
        return list(result.scalars().all())
