"""
Warp Ladger — Payment Terms Service
Organisation-scoped payment terms management with automatic initial seeding.
"""
import uuid
from typing import Optional

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.database.models import PaymentTerm, PaymentTermType
from app.payment_terms.schemas import PaymentTermCreate, PaymentTermUpdate

log = structlog.get_logger(__name__)

DEFAULT_SYSTEM_TERMS = [
    {"name": "Due immediately", "term_type": PaymentTermType.IMMEDIATE, "days": 0, "is_default_customer": False, "is_default_supplier": False},
    {"name": "7 days", "term_type": PaymentTermType.DAYS_AFTER_INVOICE, "days": 7, "is_default_customer": False, "is_default_supplier": False},
    {"name": "14 days", "term_type": PaymentTermType.DAYS_AFTER_INVOICE, "days": 14, "is_default_customer": False, "is_default_supplier": False},
    {"name": "30 days", "term_type": PaymentTermType.DAYS_AFTER_INVOICE, "days": 30, "is_default_customer": True, "is_default_supplier": True},
    {"name": "60 days", "term_type": PaymentTermType.DAYS_AFTER_INVOICE, "days": 60, "is_default_customer": False, "is_default_supplier": False},
    {"name": "End of next month", "term_type": PaymentTermType.DAYS_AFTER_MONTH_END, "days": 30, "is_default_customer": False, "is_default_supplier": False},
]


class PaymentTermsService:
    @staticmethod
    async def ensure_default_terms(db: AsyncSession, org_id: uuid.UUID) -> None:
        """Seed initial payment terms for an organisation if none exist."""
        result = await db.execute(
            select(PaymentTerm).where(PaymentTerm.organisation_id == org_id).limit(1)
        )
        if result.scalar_one_or_none() is None:
            for item in DEFAULT_SYSTEM_TERMS:
                term = PaymentTerm(
                    organisation_id=org_id,
                    name=item["name"],
                    term_type=item["term_type"],
                    days=item["days"],
                    is_default_customer=item["is_default_customer"],
                    is_default_supplier=item["is_default_supplier"],
                    active=True,
                )
                db.add(term)
            await db.flush()
            log.info("payment_terms_seeded_for_org", org_id=str(org_id))

    @staticmethod
    async def list_terms(
        db: AsyncSession, org_id: uuid.UUID, active_only: bool = False
    ) -> list[PaymentTerm]:
        await PaymentTermsService.ensure_default_terms(db, org_id)
        query = select(PaymentTerm).where(PaymentTerm.organisation_id == org_id)
        if active_only:
            query = query.where(PaymentTerm.active.is_(True))
        query = query.order_by(PaymentTerm.days.asc(), PaymentTerm.name.asc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_term(
        db: AsyncSession, org_id: uuid.UUID, term_id: uuid.UUID
    ) -> PaymentTerm:
        result = await db.execute(
            select(PaymentTerm)
            .where(PaymentTerm.id == term_id)
            .where(PaymentTerm.organisation_id == org_id)
        )
        term = result.scalar_one_or_none()
        if not term:
            raise NotFoundError("Payment term not found in this organisation.")
        return term

    @staticmethod
    async def create_term(
        db: AsyncSession, org_id: uuid.UUID, data: PaymentTermCreate
    ) -> PaymentTerm:
        # Check duplicate name in org
        existing = await db.execute(
            select(PaymentTerm)
            .where(PaymentTerm.organisation_id == org_id)
            .where(PaymentTerm.name == data.name.strip())
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"A payment term named '{data.name.strip()}' already exists.")

        # Reset existing defaults if this one is set as default
        if data.is_default_customer:
            await db.execute(
                update(PaymentTerm)
                .where(PaymentTerm.organisation_id == org_id)
                .values(is_default_customer=False)
            )
        if data.is_default_supplier:
            await db.execute(
                update(PaymentTerm)
                .where(PaymentTerm.organisation_id == org_id)
                .values(is_default_supplier=False)
            )

        term = PaymentTerm(
            organisation_id=org_id,
            name=data.name.strip(),
            term_type=data.term_type,
            days=data.days,
            is_default_customer=data.is_default_customer,
            is_default_supplier=data.is_default_supplier,
            active=data.active,
        )
        db.add(term)
        await db.flush()
        log.info("payment_term_created", org_id=str(org_id), term_id=str(term.id), name=term.name)
        return term

    @staticmethod
    async def update_term(
        db: AsyncSession, org_id: uuid.UUID, term_id: uuid.UUID, data: PaymentTermUpdate
    ) -> tuple[PaymentTerm, dict]:
        term = await PaymentTermsService.get_term(db, org_id, term_id)
        diff = {}

        if data.name is not None and data.name.strip() != term.name:
            # Check duplicate name
            existing = await db.execute(
                select(PaymentTerm)
                .where(PaymentTerm.organisation_id == org_id)
                .where(PaymentTerm.name == data.name.strip())
                .where(PaymentTerm.id != term_id)
            )
            if existing.scalar_one_or_none():
                raise ConflictError(f"A payment term named '{data.name.strip()}' already exists.")
            diff["name"] = {"before": term.name, "after": data.name.strip()}
            term.name = data.name.strip()

        if data.term_type is not None and data.term_type != term.term_type:
            diff["term_type"] = {"before": term.term_type.value, "after": data.term_type.value}
            term.term_type = data.term_type

        if data.days is not None and data.days != term.days:
            diff["days"] = {"before": term.days, "after": data.days}
            term.days = data.days

        if data.is_default_customer is not None and data.is_default_customer != term.is_default_customer:
            diff["is_default_customer"] = {"before": term.is_default_customer, "after": data.is_default_customer}
            if data.is_default_customer:
                await db.execute(
                    update(PaymentTerm)
                    .where(PaymentTerm.organisation_id == org_id)
                    .values(is_default_customer=False)
                )
            term.is_default_customer = data.is_default_customer

        if data.is_default_supplier is not None and data.is_default_supplier != term.is_default_supplier:
            diff["is_default_supplier"] = {"before": term.is_default_supplier, "after": data.is_default_supplier}
            if data.is_default_supplier:
                await db.execute(
                    update(PaymentTerm)
                    .where(PaymentTerm.organisation_id == org_id)
                    .values(is_default_supplier=False)
                )
            term.is_default_supplier = data.is_default_supplier

        if data.active is not None and data.active != term.active:
            diff["active"] = {"before": term.active, "after": data.active}
            term.active = data.active

        await db.flush()
        return term, diff

    @staticmethod
    async def delete_term(db: AsyncSession, org_id: uuid.UUID, term_id: uuid.UUID) -> None:
        term = await PaymentTermsService.get_term(db, org_id, term_id)
        # Soft-deactivate if contacts reference it, or remove if unused
        term.active = False
        await db.flush()
        log.info("payment_term_deactivated", org_id=str(org_id), term_id=str(term_id))
