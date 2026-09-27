"""
Warp Ladger — Bill Sequence Service
Generates concurrency-safe, sequential internal bill numbers per organisation.

Architecture:
  - `organisation_bill_sequences` holds the counter (prefix, next_number, padding)
  - Row is locked with SELECT ... FOR UPDATE inside the calling transaction
  - Caller commits the enclosing transaction; we never issue a separate COMMIT here
  - If no sequence row exists, one is created automatically
"""
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import OrganisationBillSequence

log = structlog.get_logger(__name__)

DEFAULT_PREFIX = "BILL-"
DEFAULT_PADDING = 6


class BillSequenceService:
    """
    Generates the next internal bill number for an organisation.

    MUST be called inside an open database transaction.
    The row lock (FOR UPDATE) prevents concurrent duplicate generation.
    """

    @staticmethod
    async def generate_bill_number(db: AsyncSession, org_id: uuid.UUID) -> str:
        """
        Atomically generate the next internal bill number for the given organisation.
        Example output: BILL-000001
        """
        # Lock the sequence row for this organisation
        stmt = (
            select(OrganisationBillSequence)
            .where(OrganisationBillSequence.organisation_id == org_id)
            .where(OrganisationBillSequence.prefix == DEFAULT_PREFIX)
        )
        if db.bind and db.bind.dialect.name != "sqlite":
            stmt = stmt.with_for_update()

        result = await db.execute(stmt)
        seq = result.scalar_one_or_none()

        if seq is None:
            # First bill for this organisation — create the sequence row
            seq = OrganisationBillSequence(
                organisation_id=org_id,
                prefix=DEFAULT_PREFIX,
                next_number=1,
                padding=DEFAULT_PADDING,
            )
            db.add(seq)
            await db.flush()

        number_str = str(seq.next_number).zfill(seq.padding)
        bill_number = f"{seq.prefix}{number_str}"

        seq.next_number += 1
        await db.flush()

        log.info(
            "bill_number_generated",
            org_id=str(org_id),
            bill_number=bill_number,
        )
        return bill_number

    @staticmethod
    async def get_sequence_info(db: AsyncSession, org_id: uuid.UUID) -> dict:
        """Return current sequence state."""
        result = await db.execute(
            select(OrganisationBillSequence)
            .where(OrganisationBillSequence.organisation_id == org_id)
        )
        seq = result.scalar_one_or_none()
        if seq is None:
            return {
                "prefix": DEFAULT_PREFIX,
                "next_number": 1,
                "padding": DEFAULT_PADDING,
                "next_bill_number": f"{DEFAULT_PREFIX}{'1'.zfill(DEFAULT_PADDING)}",
            }
        number_str = str(seq.next_number).zfill(seq.padding)
        return {
            "prefix": seq.prefix,
            "next_number": seq.next_number,
            "padding": seq.padding,
            "next_bill_number": f"{seq.prefix}{number_str}",
        }
