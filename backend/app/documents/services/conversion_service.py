"""
Warp Ladger — Document to Draft Bill Conversion Service
Maps accepted document extraction into Phase 4 BillService.create_draft.
Guarantees:
  - One bill engine (no separate AI bill model).
  - Strict idempotency (double-clicks return the existing bill).
  - Source file attachment as ORIGINAL_INVOICE.
  - Full auditability.
"""
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.bills.schemas import BillCreate, BillLineCreate
from app.bills.service import BillService
from app.core.exceptions import ConflictError, NotFoundError, ValidationFailedError
from app.database.models import (
    Bill,
    CapturedDocument,
    Contact,
    ContactType,
    DocumentExtraction,
    DocumentProcessingStatus,
    TaxRate,
)
from app.documents.schemas import CreateBillFromExtractionRequest

log = structlog.get_logger(__name__)


class DocumentConversionService:
    """Converts a captured document extraction into a canonical Phase 4 draft bill."""

    @staticmethod
    async def convert_to_draft_bill(
        db: AsyncSession,
        org_id: uuid.UUID,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        request: CreateBillFromExtractionRequest,
    ) -> Bill:
        # 1. Fetch document & extraction
        result = await db.execute(
            select(CapturedDocument)
            .where(CapturedDocument.id == document_id)
            .where(CapturedDocument.organisation_id == org_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise NotFoundError("Captured document not found in organisation.")

        # 2. Idempotency guard: If bill already created from this document, return it
        if doc.created_bill_id:
            existing_bill = await BillService.get_bill(db, org_id, doc.created_bill_id)
            log.info(
                "bill_already_created_for_document",
                doc_id=str(doc.id),
                bill_id=str(doc.created_bill_id),
            )
            return existing_bill

        # Retrieve current extraction
        ext_res = await db.execute(
            select(DocumentExtraction)
            .where(DocumentExtraction.document_id == doc.id)
            .where(DocumentExtraction.is_current.is_(True))
        )
        ext = ext_res.scalar_one_or_none()
        if not ext:
            raise ValidationFailedError(
                "Cannot create bill: document has no active extraction result."
            )

        # 3. Resolve Supplier
        supplier_id = request.supplier_id or ext.matched_supplier_id

        # If user chose to create a new supplier or no supplier exists
        if not supplier_id and (request.create_new_supplier or request.new_supplier_name):
            supplier_name = (
                request.new_supplier_name
                or ext.supplier_name_normalized
                or ext.supplier_name_raw
                or "Unknown Supplier"
            )
            new_contact = Contact(
                organisation_id=org_id,
                contact_type=ContactType.SUPPLIER,
                business_name=supplier_name,
                email=ext.supplier_email,
                phone=ext.supplier_phone,
                vat_number=ext.supplier_vat_number,
                company_number=ext.supplier_company_number,
            )
            db.add(new_contact)
            await db.flush()
            supplier_id = new_contact.id
            log.info("created_new_supplier_from_extraction", supplier_id=str(supplier_id), name=supplier_name)

        if not supplier_id:
            raise ValidationFailedError(
                "A supplier must be selected or created before converting extraction to a draft bill."
            )

        # Verify supplier exists in this organisation
        supp_check = await db.execute(
            select(Contact)
            .where(Contact.id == supplier_id)
            .where(Contact.organisation_id == org_id)
            .where(Contact.deleted_at.is_(None))
        )
        supplier = supp_check.scalar_one_or_none()
        if not supplier:
            raise NotFoundError("Selected supplier not found in this organisation.")

        # 4. Resolve default Tax Rate in organisation
        from app.invoices.tax_service import TaxRateService
        await TaxRateService.ensure_default_rates(db, org_id)

        tax_rate_id: Optional[uuid.UUID] = None
        tax_res = await db.execute(
            select(TaxRate)
            .where(TaxRate.organisation_id == org_id)
            .where(TaxRate.active.is_(True))
        )
        tax_rates = tax_res.scalars().all()
        for tr in tax_rates:
            if Decimal(str(tr.rate)) in (Decimal("20.00"), Decimal("20.0000")):
                tax_rate_id = tr.id
                break
        if not tax_rate_id and tax_rates:
            tax_rate_id = tax_rates[0].id

        # 5. Build Lines
        lines: list[BillLineCreate] = []

        # Load extracted lines
        from app.database.models import DocumentExtractionLine
        line_records = (
            (
                await db.execute(
                    select(DocumentExtractionLine)
                    .where(DocumentExtractionLine.extraction_id == ext.id)
                    .order_by(DocumentExtractionLine.position)
                )
            )
            .scalars()
            .all()
        )

        if line_records:
            for l in line_records:
                qty = l.quantity if (l.quantity and l.quantity > 0) else Decimal("1.00")
                price = l.unit_price if l.unit_price is not None else (l.net_amount or Decimal("0.00"))
                lines.append(
                    BillLineCreate(
                        description=l.description or f"Invoice Item {l.position + 1}",
                        quantity=qty,
                        unit_price=price,
                        tax_rate_id=tax_rate_id,
                        expense_account_id=request.expense_account_id,
                        purchase_category=request.purchase_category or "General Expense",
                        position=l.position,
                    )
                )
        else:
            # Summary-only fallback line
            subtotal = ext.subtotal if ext.subtotal is not None else Decimal("0.00")
            lines.append(
                BillLineCreate(
                    description=f"Supplier invoice {ext.invoice_number or doc.original_filename} (Summary Line)",
                    quantity=Decimal("1.00"),
                    unit_price=subtotal,
                    tax_rate_id=tax_rate_id,
                    expense_account_id=request.expense_account_id,
                    purchase_category=request.purchase_category or "General Expense",
                    position=0,
                )
            )

        # 6. Assemble BillCreate data
        inv_number = ext.invoice_number or f"INV-{uuid.uuid4().hex[:8].upper()}"
        bill_date = ext.invoice_date or datetime.now(UTC)

        bill_create_data = BillCreate(
            supplier_id=supplier_id,
            supplier_invoice_number=inv_number,
            bill_date=bill_date,
            due_date=ext.due_date,
            currency=ext.currency or "GBP",
            supplier_reference=ext.reference,
            purchase_order_reference=ext.purchase_order_number,
            notes=request.notes,
            internal_notes=request.internal_notes,
            lines=lines,
            file_ids=[doc.file_id],
            duplicate_override_reason=request.duplicate_override_reason,
            source_document_id=doc.id,
            source_extraction_id=ext.id,
        )

        # 7. Call Phase 4 BillService.create_draft
        bill = await BillService.create_draft(
            db=db,
            org_id=org_id,
            user_id=user_id,
            data=bill_create_data,
        )

        # 8. Link bill to document and mark as converted
        doc.created_bill_id = bill.id
        doc.processing_status = DocumentProcessingStatus.CONVERTED_TO_BILL
        await db.flush()

        await AuditService.log_static(
            db=db,
            action="DOCUMENT_CONVERTED_TO_BILL",
            resource_type="captured_document",
            resource_id=str(doc.id),
            organisation_id=org_id,
            user_id=user_id,
            diff={
                "bill_id": str(bill.id),
                "internal_bill_number": bill.internal_bill_number,
                "supplier_invoice_number": bill.supplier_invoice_number,
                "total": str(bill.total),
            },
        )

        log.info(
            "document_converted_to_draft_bill",
            doc_id=str(doc.id),
            bill_id=str(bill.id),
            bill_number=bill.internal_bill_number,
        )

        return bill
