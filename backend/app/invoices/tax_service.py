"""
Warp Ladger — Tax Rate Service
Organisation-scoped tax rate management with default seeding.
"""
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.database.models import TaxRate, TaxType
from app.invoices.schemas import TaxRateCreate, TaxRateUpdate

log = structlog.get_logger(__name__)

# Default tax rates seeded on first use (UK-centric defaults)
DEFAULT_TAX_RATES = [
    {"name": "Standard Rate", "code": "STD20", "rate": "20.0000", "tax_type": TaxType.STANDARD},
    {"name": "Reduced Rate", "code": "RED5", "rate": "5.0000", "tax_type": TaxType.REDUCED},
    {"name": "Zero Rate", "code": "ZERO", "rate": "0.0000", "tax_type": TaxType.ZERO},
    {"name": "Exempt", "code": "EXEMPT", "rate": "0.0000", "tax_type": TaxType.EXEMPT},
    {"name": "No VAT", "code": "NOVAT", "rate": "0.0000", "tax_type": TaxType.OUTSIDE_SCOPE},
]


class TaxRateService:

    @staticmethod
    async def ensure_default_rates(db: AsyncSession, org_id: uuid.UUID) -> None:
        """Seed initial tax rates for an organisation if none exist."""
        result = await db.execute(
            select(TaxRate).where(TaxRate.organisation_id == org_id).limit(1)
        )
        if result.scalar_one_or_none() is None:
            for item in DEFAULT_TAX_RATES:
                rate = TaxRate(
                    organisation_id=org_id,
                    name=item["name"],
                    code=item["code"],
                    rate=item["rate"],
                    tax_type=item["tax_type"],
                    active=True,
                )
                db.add(rate)
            await db.flush()
            log.info("tax_rates_seeded", org_id=str(org_id))

    @staticmethod
    async def list_rates(
        db: AsyncSession,
        org_id: uuid.UUID,
        active_only: bool = True,
    ) -> list[TaxRate]:
        await TaxRateService.ensure_default_rates(db, org_id)
        query = select(TaxRate).where(TaxRate.organisation_id == org_id)
        if active_only:
            query = query.where(TaxRate.active.is_(True))
        query = query.order_by(TaxRate.rate.asc(), TaxRate.name.asc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_rate(
        db: AsyncSession,
        org_id: uuid.UUID,
        tax_rate_id: uuid.UUID,
    ) -> TaxRate:
        result = await db.execute(
            select(TaxRate)
            .where(TaxRate.id == tax_rate_id)
            .where(TaxRate.organisation_id == org_id)
        )
        rate = result.scalar_one_or_none()
        if rate is None:
            raise NotFoundError("Tax rate not found.")
        return rate

    @staticmethod
    async def create_rate(
        db: AsyncSession,
        org_id: uuid.UUID,
        data: TaxRateCreate,
    ) -> TaxRate:
        # Check for duplicate code within org
        existing = await db.execute(
            select(TaxRate)
            .where(TaxRate.organisation_id == org_id)
            .where(TaxRate.code == data.code.upper())
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"A tax rate with code '{data.code}' already exists.")

        rate = TaxRate(
            organisation_id=org_id,
            **data.model_dump(),
        )
        db.add(rate)
        await db.flush()
        await db.refresh(rate)
        return rate

    @staticmethod
    async def update_rate(
        db: AsyncSession,
        org_id: uuid.UUID,
        tax_rate_id: uuid.UUID,
        data: TaxRateUpdate,
    ) -> TaxRate:
        rate = await TaxRateService.get_rate(db, org_id, tax_rate_id)
        for key, val in data.model_dump(exclude_none=True).items():
            setattr(rate, key, val)
        await db.flush()
        await db.refresh(rate)
        return rate

    @staticmethod
    async def delete_rate(
        db: AsyncSession,
        org_id: uuid.UUID,
        tax_rate_id: uuid.UUID,
    ) -> None:
        """Soft-delete by deactivating — preserves historical line references."""
        rate = await TaxRateService.get_rate(db, org_id, tax_rate_id)
        rate.active = False
        await db.flush()
