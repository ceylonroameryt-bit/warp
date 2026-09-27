"""
Warp Ladger — Invoice Sequence Service
Generates concurrency-safe, sequential invoice numbers per organisation.

Architecture:
  - `organisation_invoice_sequences` holds the counter (prefix, next_number, padding)
  - Row is locked with SELECT ... FOR UPDATE inside the calling transaction
  - Caller commits the enclosing transaction; we never issue a separate COMMIT here
  - If no sequence row exists, one is created automatically
"""
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import OrganisationInvoiceSequence

log = structlog.get_logger(__name__)

DEFAULT_PREFIX = "INV-"
DEFAULT_PADDING = 6


class SequenceService:
    """
    Generates the next invoice number for an organisation.

    MUST be called inside an open database transaction.
    The row lock (FOR UPDATE) prevents concurrent duplicate generation.
    """

    @staticmethod
    async def generate_invoice_number(db: AsyncSession, org_id: uuid.UUID) -> str:
        """
        Atomically generate the next invoice number for the given organisation.

        Example output: INV-000105

        Uses SELECT ... FOR UPDATE to prevent concurrent duplicates.
        The sequence row is created on first use.
        """
        # Lock the sequence row for this organisation
        result = await db.execute(
            select(OrganisationInvoiceSequence)
            .where(OrganisationInvoiceSequence.organisation_id == org_id)
            .where(OrganisationInvoiceSequence.prefix == DEFAULT_PREFIX)
            .with_for_update()  # Row-level exclusive lock
        )
        seq = result.scalar_one_or_none()

        if seq is None:
            # First invoice for this organisation — create the sequence row
            seq = OrganisationInvoiceSequence(
                organisation_id=org_id,
                prefix=DEFAULT_PREFIX,
                next_number=1,
                padding=DEFAULT_PADDING,
            )
            db.add(seq)
            await db.flush()  # Assign PK without committing

        # Generate the invoice number from current counter
        number_str = str(seq.next_number).zfill(seq.padding)
        invoice_number = f"{seq.prefix}{number_str}"

        # Increment counter
        seq.next_number += 1
        await db.flush()

        log.info(
            "invoice_number_generated",
            org_id=str(org_id),
            invoice_number=invoice_number,
        )
        return invoice_number

    @staticmethod
    async def get_sequence_info(
        db: AsyncSession, org_id: uuid.UUID
    ) -> dict:
        """Return current sequence state (for settings display)."""
        result = await db.execute(
            select(OrganisationInvoiceSequence)
            .where(OrganisationInvoiceSequence.organisation_id == org_id)
        )
        seq = result.scalar_one_or_none()
        if seq is None:
            return {
                "prefix": DEFAULT_PREFIX,
                "next_number": 1,
                "padding": DEFAULT_PADDING,
                "next_invoice_number": f"{DEFAULT_PREFIX}{'1'.zfill(DEFAULT_PADDING)}",
            }
        number_str = str(seq.next_number).zfill(seq.padding)
        return {
            "prefix": seq.prefix,
            "next_number": seq.next_number,
            "padding": seq.padding,
            "next_invoice_number": f"{seq.prefix}{number_str}",
        }
