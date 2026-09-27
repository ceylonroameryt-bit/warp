"""Warp Ladger — Memberships Service"""
import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.database.models import Membership, MembershipStatus, Role, User

log = structlog.get_logger(__name__)


class MembershipService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_members(self, org_id: uuid.UUID) -> list[Membership]:
        result = await self.db.execute(
            select(Membership)
            .where(Membership.organisation_id == org_id)
            .where(Membership.status != MembershipStatus.invited.value)
            .options(selectinload(Membership.user), selectinload(Membership.role))
            .order_by(Membership.created_at)
        )
        return list(result.scalars().all())

    async def _assert_not_last_owner(self, org_id: uuid.UUID, target_user_id: uuid.UUID) -> None:
        owner_role_res = await self.db.execute(select(Role).where(Role.name == "owner"))
        owner_role = owner_role_res.scalar_one_or_none()
        if not owner_role:
            return
        active_owners_res = await self.db.execute(
            select(Membership)
            .where(Membership.organisation_id == org_id)
            .where(Membership.role_id == owner_role.id)
            .where(Membership.status == MembershipStatus.active)
        )
        active_owners = active_owners_res.scalars().all()
        if len(active_owners) <= 1 and any(m.user_id == target_user_id for m in active_owners):
            raise PermissionDeniedError("Cannot demote, suspend, or remove the last active Owner of the organisation.")

    async def update_member_role(
        self,
        *,
        org_id: uuid.UUID,
        target_user_id: uuid.UUID,
        new_role_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> Membership:
        if actor_id == target_user_id:
            raise PermissionDeniedError("You cannot change your own role.")

        membership = await self._get_membership(org_id, target_user_id)

        # Ensure new role belongs to this org or is a system role
        role_result = await self.db.execute(
            select(Role).where(Role.id == new_role_id)
        )
        role = role_result.scalar_one_or_none()
        if role is None:
            raise NotFoundError("Role not found.")
        if not role.is_system and str(role.organisation_id) != str(org_id):
            raise PermissionDeniedError("Role does not belong to this organisation.")

        # If demoting from owner, guard last owner
        if str(membership.role_id) != str(new_role_id):
            await self._assert_not_last_owner(org_id, target_user_id)

        membership.role_id = new_role_id
        await self.db.flush()
        return membership

    async def suspend_member(
        self, *, org_id: uuid.UUID, target_user_id: uuid.UUID, actor_id: uuid.UUID
    ) -> Membership:
        if actor_id == target_user_id:
            raise PermissionDeniedError("You cannot suspend yourself.")
        await self._assert_not_last_owner(org_id, target_user_id)
        membership = await self._get_membership(org_id, target_user_id)
        membership.status = MembershipStatus.suspended
        await self.db.flush()
        return membership

    async def reactivate_member(
        self, *, org_id: uuid.UUID, target_user_id: uuid.UUID
    ) -> Membership:
        membership = await self._get_membership(
            org_id, target_user_id, allow_suspended=True
        )
        membership.status = MembershipStatus.active
        await self.db.flush()
        return membership

    async def remove_member(
        self, *, org_id: uuid.UUID, target_user_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        if actor_id == target_user_id:
            raise PermissionDeniedError("You cannot remove yourself from an organisation.")
        await self._assert_not_last_owner(org_id, target_user_id)
        membership = await self._get_membership(org_id, target_user_id, allow_suspended=True)
        await self.db.delete(membership)
        await self.db.flush()

    async def _get_membership(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        allow_suspended: bool = False,
    ) -> Membership:
        q = (
            select(Membership)
            .where(Membership.organisation_id == org_id)
            .where(Membership.user_id == user_id)
        )
        if not allow_suspended:
            q = q.where(Membership.status == MembershipStatus.active)
        result = await self.db.execute(q)
        membership = result.scalar_one_or_none()
        if membership is None:
            raise NotFoundError("Membership not found.")
        return membership
