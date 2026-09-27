"""
Warp Ladger — Duplicate Bill Detection Service
Detects potential duplicate supplier bills using:
- Normalized supplier invoice numbers
- File SHA-256 checksums
- Multi-factor fuzzy scoring (supplier, date, total, currency)
"""
import re
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.bills.schemas import DuplicateCheckResponse, DuplicateMatch
from app.database.models import Bill, BillDocument, BillStatus, Contact

log = structlog.get_logger(__name__)


def normalize_invoice_number(inv_num: str) -> str:
    """
    Normalise invoice numbers for deduplication.
    Strips whitespace, hyphens, slashes, punctuation, and lowercases.
    e.g. 'MS-882931' -> 'ms882931', 'MS 882931' -> 'ms882931'
    """
    if not inv_num:
        return ""
    return re.sub(r"[^a-zA-Z0-9]", "", inv_num).lower()


class DuplicateBillService:
    """
    Scoring & duplicate detection engine for supplier bills.
    """

    @staticmethod
    async def check_duplicates(
        db: AsyncSession,
        org_id: uuid.UUID,
        supplier_id: uuid.UUID,
        supplier_invoice_number: str,
        bill_date: Optional[datetime] = None,
        total: Optional[Decimal] = None,
        file_checksum: Optional[str] = None,
        exclude_bill_id: Optional[uuid.UUID] = None,
    ) -> DuplicateCheckResponse:
        """
        Evaluate if a bill might be a duplicate within the organisation.
        """
        normalized_num = normalize_invoice_number(supplier_invoice_number)
        matches: list[DuplicateMatch] = []
        highest_severity = "NONE"

        # 1. Exact or normalized invoice number match for the SAME supplier
        stmt = (
            select(Bill)
            .where(Bill.organisation_id == org_id)
            .where(Bill.supplier_id == supplier_id)
            .where(Bill.status != BillStatus.VOID)
            .options(selectinload(Bill.supplier))
        )
        if exclude_bill_id:
            stmt = stmt.where(Bill.id != exclude_bill_id)

        result = await db.execute(stmt)
        existing_bills = result.scalars().all()

        for b in existing_bills:
            score = 0
            match_reasons = []
            match_type = "POSSIBLE_MATCH"

            # Check normalized invoice number match
            if b.supplier_invoice_number_normalized == normalized_num:
                score += 80
                match_reasons.append(f"Same invoice number ('{b.supplier_invoice_number}') for this supplier")
                match_type = "EXACT_INVOICE_NUMBER"
            elif normalized_num in b.supplier_invoice_number_normalized or b.supplier_invoice_number_normalized in normalized_num:
                score += 40
                match_reasons.append(f"Similar invoice number ('{b.supplier_invoice_number}')")

            # Check amount match
            if total is not None and abs(Decimal(str(b.total)) - Decimal(str(total))) < Decimal("0.01"):
                score += 15
                match_reasons.append(f"Identical total amount ({b.currency} {b.total:.2f})")

            # Check date match (within 7 days)
            if bill_date and b.bill_date:
                days_diff = abs((b.bill_date.date() - bill_date.date()).days)
                if days_diff == 0:
                    score += 10
                    match_reasons.append("Identical bill date")
                elif days_diff <= 7:
                    score += 5
                    match_reasons.append(f"Bill date within {days_diff} days")

            if score >= 50:
                s_name = b.supplier.business_name if b.supplier else (b.supplier_name_snapshot or "Unknown Supplier")
                matches.append(
                    DuplicateMatch(
                        bill_id=b.id,
                        internal_bill_number=b.internal_bill_number,
                        supplier_invoice_number=b.supplier_invoice_number,
                        supplier_name=s_name,
                        bill_date=b.bill_date,
                        total=Decimal(str(b.total)),
                        currency=b.currency,
                        status=b.status.value,
                        match_type=match_type,
                        confidence_score=min(score, 100),
                        reason="; ".join(match_reasons),
                    )
                )

        # 2. File checksum match across the organisation
        if file_checksum:
            doc_stmt = (
                select(BillDocument)
                .join(Bill, Bill.id == BillDocument.bill_id)
                .where(BillDocument.organisation_id == org_id)
                .where(BillDocument.checksum_sha256 == file_checksum)
                .where(Bill.status != BillStatus.VOID)
                .options(selectinload(BillDocument.bill).selectinload(Bill.supplier))
            )
            if exclude_bill_id:
                doc_stmt = doc_stmt.where(BillDocument.bill_id != exclude_bill_id)

            doc_result = await db.execute(doc_stmt)
            matching_docs = doc_result.scalars().all()

            for doc in matching_docs:
                b = doc.bill
                # Avoid duplicate entries in matches list
                if any(m.bill_id == b.id for m in matches):
                    continue

                s_name = b.supplier.business_name if b.supplier else (b.supplier_name_snapshot or "Unknown Supplier")
                matches.append(
                    DuplicateMatch(
                        bill_id=b.id,
                        internal_bill_number=b.internal_bill_number,
                        supplier_invoice_number=b.supplier_invoice_number,
                        supplier_name=s_name,
                        bill_date=b.bill_date,
                        total=Decimal(str(b.total)),
                        currency=b.currency,
                        status=b.status.value,
                        match_type="EXACT_FILE_CHECKSUM",
                        confidence_score=95,
                        reason="Exact uploaded invoice document SHA-256 checksum match",
                    )
                )

        # Determine overall severity
        if any(m.match_type == "EXACT_INVOICE_NUMBER" for m in matches):
            highest_severity = "BLOCK"
        elif any(m.match_type == "EXACT_FILE_CHECKSUM" for m in matches):
            highest_severity = "WARNING"
        elif len(matches) > 0:
            highest_severity = "WARNING"

        return DuplicateCheckResponse(
            is_duplicate=len(matches) > 0,
            severity=highest_severity,
            matches=matches,
        )
