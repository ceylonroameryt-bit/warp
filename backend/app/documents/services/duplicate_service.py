"""
Warp Ladger — Document Duplicate Detection Engine
Implements 3-layer protection:
  Layer 1: Exact file checksum (SHA-256)
  Layer 2: Exact supplier + invoice number
  Layer 3: Fuzzy supplier + invoice number + date + total
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bills.duplicate_service import normalize_invoice_number
from app.database.models import Bill, BillStatus, CapturedDocument, DocumentExtraction
from app.documents.schemas import DuplicateCheckResponse


class DocumentDuplicateService:
    """Multi-tiered duplicate detection for captured financial documents."""

    @staticmethod
    async def check_duplicates(
        db: AsyncSession,
        org_id: uuid.UUID,
        doc_id: uuid.UUID,
        checksum_sha256: str,
        supplier_id: Optional[uuid.UUID] = None,
        invoice_number: Optional[str] = None,
        invoice_date: Optional[datetime] = None,
        total: Optional[Decimal] = None,
    ) -> DuplicateCheckResponse:
        # ── Layer 1: Exact File Check (SHA-256) ───────────────
        file_query = (
            select(CapturedDocument)
            .where(CapturedDocument.organisation_id == org_id)
            .where(CapturedDocument.checksum_sha256 == checksum_sha256)
            .where(CapturedDocument.id != doc_id)
        )
        file_res = await db.execute(file_query)
        existing_doc = file_res.scalars().first()
        if existing_doc:
            return DuplicateCheckResponse(
                is_duplicate=True,
                severity="BLOCK",
                duplicate_document_id=existing_doc.id,
                duplicate_bill_id=existing_doc.created_bill_id,
                duplicate_invoice_number=None,
                reason=f"Identical file previously uploaded on {existing_doc.created_at.strftime('%d %b %Y')} ({existing_doc.original_filename}).",
            )

        # ── Layer 2: Supplier + Invoice Number Check ──────────
        if supplier_id and invoice_number:
            norm_inv = normalize_invoice_number(invoice_number)

            # Check existing Bills in this tenant
            bill_query = (
                select(Bill)
                .where(Bill.organisation_id == org_id)
                .where(Bill.supplier_id == supplier_id)
                .where(Bill.supplier_invoice_number_normalized == norm_inv)
                .where(Bill.status != BillStatus.VOID)
            )
            bill_res = await db.execute(bill_query)
            existing_bill = bill_res.scalars().first()
            if existing_bill:
                return DuplicateCheckResponse(
                    is_duplicate=True,
                    severity="BLOCK",
                    duplicate_bill_id=existing_bill.id,
                    duplicate_invoice_number=existing_bill.supplier_invoice_number,
                    reason=(
                        f"A bill with invoice number '{existing_bill.supplier_invoice_number}' "
                        f"already exists for this supplier ({existing_bill.internal_bill_number or 'Draft'})."
                    ),
                )

            # Check other Captured Documents in this tenant
            doc_query = (
                select(DocumentExtraction)
                .where(DocumentExtraction.organisation_id == org_id)
                .where(DocumentExtraction.document_id != doc_id)
                .where(DocumentExtraction.is_current.is_(True))
                .where(DocumentExtraction.matched_supplier_id == supplier_id)
            )
            doc_res = await db.execute(doc_query)
            for ext in doc_res.scalars().all():
                if ext.invoice_number and normalize_invoice_number(ext.invoice_number) == norm_inv:
                    return DuplicateCheckResponse(
                        is_duplicate=True,
                        severity="BLOCK",
                        duplicate_document_id=ext.document_id,
                        duplicate_bill_id=ext.duplicate_bill_id,
                        duplicate_invoice_number=ext.invoice_number,
                        reason=f"Another uploaded document already has invoice number '{ext.invoice_number}' for this supplier.",
                    )

        # ── Layer 3: Fuzzy Supplier + Date + Total Check ──────
        if supplier_id and total is not None and invoice_date:
            bill_query = (
                select(Bill)
                .where(Bill.organisation_id == org_id)
                .where(Bill.supplier_id == supplier_id)
                .where(Bill.status != BillStatus.VOID)
            )
            bill_res = await db.execute(bill_query)
            for b in bill_res.scalars().all():
                if abs(b.total - total) <= Decimal("0.05"):
                    # Check if date within 3 days
                    b_date = b.bill_date.date() if hasattr(b.bill_date, "date") else b.bill_date
                    inv_date = invoice_date.date() if hasattr(invoice_date, "date") else invoice_date
                    day_diff = abs((b_date - inv_date).days)
                    if day_diff <= 3:
                        return DuplicateCheckResponse(
                            is_duplicate=True,
                            severity="WARN",
                            duplicate_bill_id=b.id,
                            duplicate_invoice_number=b.supplier_invoice_number,
                            reason=(
                                f"Possible duplicate: existing bill '{b.supplier_invoice_number}' "
                                f"has the same amount ({b.total:.2f}) within {day_diff} days."
                            ),
                        )

        return DuplicateCheckResponse(is_duplicate=False, severity="NONE")
