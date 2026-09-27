"""
Warp Ladger — Organisations Service
"""
import uuid
from datetime import UTC, datetime
from typing import Optional

import structlog
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.database.models import (
    Membership,
    MembershipStatus,
    Organisation,
    OrganisationStatus,
    Role,
)

log = structlog.get_logger(__name__)


class OrganisationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_organisation(
        self,
        *,
        name: str,
        owner_id: uuid.UUID,
        slug: Optional[str] = None,
        currency: str = "GBP",
        timezone: str = "Europe/London",
    ) -> Organisation:
        """Create a new organisation and assign the owner role to the creator."""
        final_slug = slug or slugify(name)

        # Ensure slug uniqueness, append suffix if needed
        existing = await self.db.execute(
            select(Organisation).where(Organisation.slug == final_slug)
        )
        if existing.scalar_one_or_none():
            final_slug = f"{final_slug}-{str(uuid.uuid4())[:8]}"

        org = Organisation(
            name=name,
            slug=final_slug,
            owner_id=owner_id,
            currency=currency,
            timezone=timezone,
        )
        self.db.add(org)
        await self.db.flush()

        # Get the system "owner" role
        role_result = await self.db.execute(
            select(Role).where(Role.name == "owner").where(Role.is_system.is_(True))
        )
        owner_role = role_result.scalar_one_or_none()
        if owner_role is None:
            raise RuntimeError("System 'owner' role not found. Run 'make seed' first.")

        membership = Membership(
            user_id=owner_id,
            organisation_id=org.id,
            role_id=owner_role.id,
            status=MembershipStatus.active,
            joined_at=datetime.now(UTC),
        )
        self.db.add(membership)
        await self.db.flush()

        log.info("organisation_created", org_id=str(org.id), slug=org.slug, owner=str(owner_id))
        return org

    async def get_organisation(
        self,
        org_id: uuid.UUID,
        *,
        require_active: bool = True,
    ) -> Organisation:
        result = await self.db.execute(
            select(Organisation)
            .where(Organisation.id == org_id)
            .where(Organisation.deleted_at.is_(None))
        )
        org = result.scalar_one_or_none()
        if org is None:
            raise NotFoundError("Organisation not found.")
        if require_active and org.status != OrganisationStatus.active:
            raise NotFoundError("Organisation is not active.")
        return org

    async def update_organisation(
        self, org_id: uuid.UUID, *, updates: dict
    ) -> Organisation:
        org = await self.get_organisation(org_id)
        for key, value in updates.items():
            if value is not None:
                setattr(org, key, value)
        await self.db.flush()
        return org

    async def list_user_organisations(self, user_id: uuid.UUID) -> list[Organisation]:
        result = await self.db.execute(
            select(Organisation)
            .join(Membership, Membership.organisation_id == Organisation.id)
            .where(Membership.user_id == user_id)
            .where(Membership.status == MembershipStatus.active)
            .where(Organisation.deleted_at.is_(None))
            .order_by(Organisation.name)
        )
        return list(result.scalars().all())

    async def soft_delete_organisation(self, org_id: uuid.UUID) -> None:
        org = await self.get_organisation(org_id)
        org.soft_delete()
        org.status = OrganisationStatus.cancelled
        log.info("organisation_deleted", org_id=str(org_id))
