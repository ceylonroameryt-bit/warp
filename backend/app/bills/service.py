"""
Warp Ladger — Bill Service (Phase 4)
Core business logic for supplier bills / payables lifecycle:
- Draft creation & editing
- Multi-line tax & decimal financial calculation via MoneyService
- Duplicate invoice detection & override tracking
- Original document attachment & checksum validation
- Submission, Approval (with supplier snapshot), Rejection, and Voiding
- Runtime OVERDUE state calculation
- Audit event emission
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import hashlib
from typing import Optional
import uuid

import structlog
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.audit.service import AuditService
from app.bills.duplicate_service import DuplicateBillService, normalize_invoice_number
from app.bills.schemas import (
    BillCreate,
    BillFilters,
    BillLineCreate,
    BillLineUpdate,
    BillUpdate,
    PurchasesMetricsResponse,
)
from app.bills.sequence_service import BillSequenceService
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from app.database.models import (
    Bill,
    BillApprovalAction,
    BillApprovalEvent,
    BillDocument,
    BillLine,
    BillStatus,
    Contact,
    ContactAddress,
    ContactStatus,
    ContactType,
    File,
    OrganisationSetting,
    PaymentTerm,
    TaxRate,
    User,
)
from app.invoices.money_service import LineCalcResult, MoneyService

log = structlog.get_logger(__name__)

EDITABLE_STATUSES = {BillStatus.DRAFT, BillStatus.REJECTED}


class BillService:
    """Primary service for supplier bills."""

    # ── Status Derivation ────────────────────────────────────
    @staticmethod
    def _effective_status(bill: Bill) -> str:
        """
        Derives the effective status.
        OVERDUE is dynamically derived when:
          (status == APPROVED or status == AWAITING_PAYMENT)
          AND amount_due > 0
          AND current_date > due_date
        """
        if bill.status in (BillStatus.APPROVED, BillStatus.AWAITING_PAYMENT):
            now = datetime.now(UTC)
            # Make due_date timezone-aware if needed
            due = bill.due_date
            if due.tzinfo is None:
                due = due.replace(tzinfo=UTC)
            if bill.amount_due > 0 and now > due:
                return "OVERDUE"
            return "AWAITING_PAYMENT"
        return bill.status.value

    # ── Helpers ──────────────────────────────────────────────
    @staticmethod
    async def _resolve_tax_rates(
        db: AsyncSession, org_id: uuid.UUID, lines: list
    ) -> dict[uuid.UUID, Decimal]:
        """Fetch active tax rate percentages for all referenced tax rate IDs."""
        rate_ids = {
            getattr(l, "tax_rate_id", None)
            for l in lines
            if getattr(l, "tax_rate_id", None) is not None
        }
        tax_map: dict[uuid.UUID, Decimal] = {}
        if rate_ids:
            result = await db.execute(
                select(TaxRate)
                .where(TaxRate.id.in_(rate_ids))
                .where(TaxRate.organisation_id == org_id)
            )
            for tr in result.scalars().all():
                tax_map[tr.id] = Decimal(str(tr.rate))
        return tax_map

    @staticmethod
    def _calculate_lines(
        lines: list, tax_map: dict[uuid.UUID, Decimal]
    ) -> tuple[list[dict], Decimal, Decimal, Decimal, Decimal]:
        """
        Calculate each line using MoneyService.
        Returns: (calc_lines, subtotal, discount_total, tax_total, total)
        """
        calc_lines = []
        subtotal = Decimal("0")
        discount_total = Decimal("0")
        tax_total = Decimal("0")

        for idx, line in enumerate(lines):
            rate = tax_map.get(getattr(line, "tax_rate_id", None), Decimal("0"))
            disc_type = line.discount_type.value if line.discount_type else None
            disc_val = getattr(line, "discount_value", Decimal("0")) or Decimal("0")

            calc: LineCalcResult = MoneyService.calculate_line(
                quantity=line.quantity,
                unit_price=line.unit_price,
                tax_rate=rate,
                discount_type=disc_type,
                discount_value=disc_val,
            )

            calc_lines.append({
                "position": idx,
                "description": line.description,
                "quantity": calc.quantity,
                "unit_price": calc.unit_price,
                "discount_type": line.discount_type,
                "discount_value": calc.discount_value,
                "net_amount": calc.net_amount,
                "tax_amount": calc.tax_amount,
                "gross_amount": calc.gross_amount,
                "tax_rate_id": getattr(line, "tax_rate_id", None),
                "tax_rate_snapshot": rate,
                "expense_account_id": getattr(line, "expense_account_id", None),
                "purchase_category": getattr(line, "purchase_category", None),
            })

            subtotal += calc.net_amount
            discount_total += calc.discount_amount
            tax_total += calc.tax_amount

        total = subtotal + tax_total
        return calc_lines, subtotal, discount_total, tax_total, total

    # ── Create Draft ─────────────────────────────────────────
    @staticmethod
    async def create_draft(
        db: AsyncSession,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        data: BillCreate,
    ) -> Bill:
        """Create a new DRAFT bill."""
        # 1. Validate supplier
        result = await db.execute(
            select(Contact)
            .where(Contact.id == data.supplier_id)
            .where(Contact.organisation_id == org_id)
            .where(Contact.deleted_at.is_(None))
        )
        supplier = result.scalar_one_or_none()
        if not supplier:
            raise NotFoundError("Supplier not found in this organisation.", code="SUPPLIER_NOT_FOUND")
        if supplier.contact_type not in (ContactType.SUPPLIER, ContactType.BOTH):
            raise BadRequestError(
                f"Contact '{supplier.business_name}' is not classified as a supplier.",
                code="INVALID_SUPPLIER_TYPE",
            )

        # 2. Check for duplicates
        dup_check = await DuplicateBillService.check_duplicates(
            db=db,
            org_id=org_id,
            supplier_id=data.supplier_id,
            supplier_invoice_number=data.supplier_invoice_number,
            bill_date=data.bill_date,
        )
        if dup_check.is_duplicate and dup_check.severity == "BLOCK" and not data.duplicate_override_reason:
            raise ConflictError(
                f"Duplicate invoice number '{data.supplier_invoice_number}' detected for this supplier. "
                "Provide an override reason to continue.",
                code="DUPLICATE_BILL",
            )

        # 3. Resolve due date from payment terms if not provided
        due_date = data.due_date
        payment_terms_id = data.payment_terms_id or supplier.payment_terms_id
        if not due_date:
            if payment_terms_id:
                pt_res = await db.execute(
                    select(PaymentTerm).where(PaymentTerm.id == payment_terms_id)
                )
                pt = pt_res.scalar_one_or_none()
                if pt:
                    due_date = data.bill_date + timedelta(days=pt.days)
            if not due_date:
                due_date = data.bill_date + timedelta(days=30)  # Default 30 days

        # 4. Generate internal bill number
        internal_bill_number = await BillSequenceService.generate_bill_number(db, org_id)

        # 5. Calculate financials
        tax_map = await BillService._resolve_tax_rates(db, org_id, data.lines)
        calc_lines, subtotal, disc_total, tax_total, total = BillService._calculate_lines(data.lines, tax_map)

        normalized_inv_num = normalize_invoice_number(data.supplier_invoice_number)

        bill = Bill(
            organisation_id=org_id,
            supplier_id=data.supplier_id,
            supplier_invoice_number=data.supplier_invoice_number,
            supplier_invoice_number_normalized=normalized_inv_num,
            internal_bill_number=internal_bill_number,
            status=BillStatus.DRAFT,
            bill_date=data.bill_date,
            due_date=due_date,
            currency=data.currency or "GBP",
            supplier_reference=data.supplier_reference,
            purchase_order_reference=data.purchase_order_reference,
            payment_terms_id=payment_terms_id,
            purchase_category_id=data.purchase_category_id,
            subtotal=subtotal,
            discount_total=disc_total,
            tax_total=tax_total,
            total=total,
            amount_paid=Decimal("0"),
            amount_due=total,
            notes=data.notes,
            internal_notes=data.internal_notes,
            created_by_id=user_id,
            version=1,
            source_document_id=data.source_document_id,
            source_extraction_id=data.source_extraction_id,
        )

        if data.duplicate_override_reason:
            bill.duplicate_override_by_id = user_id
            bill.duplicate_override_at = datetime.now(UTC)
            bill.duplicate_override_reason = data.duplicate_override_reason

        db.add(bill)
        await db.flush()

        # Add lines
        for cl in calc_lines:
            line_record = BillLine(
                organisation_id=org_id,
                bill_id=bill.id,
                **cl,
            )
            db.add(line_record)

        # Link initial files if provided
        if data.file_ids:
            for fid in data.file_ids:
                doc = BillDocument(
                    organisation_id=org_id,
                    bill_id=bill.id,
                    file_id=fid,
                    document_type="ORIGINAL_INVOICE",
                    created_by_id=user_id,
                )
                db.add(doc)

        await db.flush()

        await AuditService.log_static(
            db,
            action="BILL_CREATED",
            resource_type="bill",
            resource_id=str(bill.id),
            organisation_id=org_id,
            user_id=user_id,
            diff={"status": "DRAFT", "internal_bill_number": internal_bill_number, "total": str(total)},
        )

        if data.duplicate_override_reason:
            await AuditService.log_static(
                db,
                action="BILL_DUPLICATE_OVERRIDE",
                resource_type="bill",
                resource_id=str(bill.id),
                organisation_id=org_id,
                user_id=user_id,
                diff={"reason": data.duplicate_override_reason},
            )

        log.info("bill_draft_created", bill_id=str(bill.id), org_id=str(org_id), internal_number=internal_bill_number)
        return await BillService.get_bill(db, org_id, bill.id)

    # ── Update Draft ─────────────────────────────────────────
    @staticmethod
    async def update_draft(
        db: AsyncSession,
        org_id: uuid.UUID,
        bill_id: uuid.UUID,
        user_id: uuid.UUID,
        data: BillUpdate,
    ) -> Bill:
        """Update a DRAFT or REJECTED bill."""
        bill = await BillService.get_bill(db, org_id, bill_id)

        if bill.status not in EDITABLE_STATUSES:
            raise BadRequestError(
                f"Only DRAFT or REJECTED bills can be edited. Bills with status '{bill.status.value}' cannot be edited directly. Approved bills must be voided.",
                code="BILL_NOT_EDITABLE",
            )

        # Optimistic locking check
        if data.version is not None and data.version != bill.version:
            raise ConflictError(
                "This bill has changed since you opened it. Reload before continuing.",
                code="CONCURRENCY_CONFLICT",
            )

        # Update supplier if provided
        if data.supplier_id and data.supplier_id != bill.supplier_id:
            s_res = await db.execute(
                select(Contact)
                .where(Contact.id == data.supplier_id)
                .where(Contact.organisation_id == org_id)
                .where(Contact.deleted_at.is_(None))
            )
            supplier = s_res.scalar_one_or_none()
            if not supplier:
                raise NotFoundError("Supplier not found.", code="SUPPLIER_NOT_FOUND")
            bill.supplier_id = data.supplier_id

        # Update invoice number if provided
        if data.supplier_invoice_number:
            bill.supplier_invoice_number = data.supplier_invoice_number
            bill.supplier_invoice_number_normalized = normalize_invoice_number(data.supplier_invoice_number)

            dup_check = await DuplicateBillService.check_duplicates(
                db=db,
                org_id=org_id,
                supplier_id=bill.supplier_id,
                supplier_invoice_number=bill.supplier_invoice_number,
                exclude_bill_id=bill.id,
            )
            if dup_check.is_duplicate and dup_check.severity == "BLOCK" and not data.duplicate_override_reason:
                raise ConflictError(
                    f"Duplicate invoice number '{data.supplier_invoice_number}' detected. Provide an override reason to continue.",
                    code="DUPLICATE_BILL",
                )

        if data.duplicate_override_reason:
            bill.duplicate_override_by_id = user_id
            bill.duplicate_override_at = datetime.now(UTC)
            bill.duplicate_override_reason = data.duplicate_override_reason

        if data.bill_date:
            bill.bill_date = data.bill_date
        if data.due_date:
            bill.due_date = data.due_date
        if data.currency:
            bill.currency = data.currency
        if data.supplier_reference is not None:
            bill.supplier_reference = data.supplier_reference
        if data.purchase_order_reference is not None:
            bill.purchase_order_reference = data.purchase_order_reference
        if data.payment_terms_id is not None:
            bill.payment_terms_id = data.payment_terms_id
        if data.purchase_category_id is not None:
            bill.purchase_category_id = data.purchase_category_id
        if data.notes is not None:
            bill.notes = data.notes
        if data.internal_notes is not None:
            bill.internal_notes = data.internal_notes

        # Re-calculate lines if provided
        if data.lines is not None:
            # Remove existing lines
            for old_l in list(bill.lines):
                await db.delete(old_l)
            await db.flush()

            tax_map = await BillService._resolve_tax_rates(db, org_id, data.lines)
            calc_lines, subtotal, disc_total, tax_total, total = BillService._calculate_lines(data.lines, tax_map)

            bill.subtotal = subtotal
            bill.discount_total = disc_total
            bill.tax_total = tax_total
            bill.total = total
            bill.amount_due = total - bill.amount_paid

            for cl in calc_lines:
                line_record = BillLine(
                    organisation_id=org_id,
                    bill_id=bill.id,
                    **cl,
                )
                db.add(line_record)

        bill.version += 1
        await db.flush()

        await AuditService.log_static(
            db,
            action="BILL_UPDATED",
            resource_type="bill",
            resource_id=str(bill.id),
            organisation_id=org_id,
            user_id=user_id,
            diff={"total": str(bill.total), "version": bill.version},
        )

        return await BillService.get_bill(db, org_id, bill.id)

    # ── Delete Draft ─────────────────────────────────────────
    @staticmethod
    async def delete_draft(
        db: AsyncSession,
        org_id: uuid.UUID,
        bill_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Hard-delete a DRAFT bill."""
        bill = await BillService.get_bill(db, org_id, bill_id)
        if bill.status != BillStatus.DRAFT:
            raise BadRequestError("Only DRAFT bills can be deleted. Approved bills must be voided.", code="BILL_NOT_EDITABLE")

        await db.delete(bill)
        await db.flush()

        await AuditService.log_static(
            db,
            action="BILL_DELETED",
            resource_type="bill",
            resource_id=str(bill_id),
            organisation_id=org_id,
            user_id=user_id,
        )

    # ── Document Management ──────────────────────────────────
    @staticmethod
    async def attach_document(
        db: AsyncSession,
        org_id: uuid.UUID,
        bill_id: uuid.UUID,
        user_id: uuid.UUID,
        file_id: uuid.UUID,
        document_type: str = "ORIGINAL_INVOICE",
        checksum_sha256: Optional[str] = None,
    ) -> BillDocument:
        """Attach an uploaded document to a bill with optional checksum tracking."""
        bill = await BillService.get_bill(db, org_id, bill_id)

        # Validate file belongs to organisation
        f_res = await db.execute(
            select(File)
            .where(File.id == file_id)
            .where(File.organisation_id == org_id)
            .where(File.is_deleted.is_(False))
        )
        file_record = f_res.scalar_one_or_none()
        if not file_record:
            raise NotFoundError("File not found in this organisation.", code="FILE_NOT_FOUND")

        doc = BillDocument(
            organisation_id=org_id,
            bill_id=bill_id,
            file_id=file_id,
            document_type=document_type,
            checksum_sha256=checksum_sha256,
            created_by_id=user_id,
        )
        db.add(doc)
        await db.flush()

        await AuditService.log_static(
            db,
            action="BILL_DOCUMENT_ATTACHED",
            resource_type="bill",
            resource_id=str(bill_id),
            organisation_id=org_id,
            user_id=user_id,
            diff={"file_id": str(file_id), "document_type": document_type, "filename": file_record.filename},
        )

        return doc

    @staticmethod
    async def remove_document(
        db: AsyncSession,
        org_id: uuid.UUID,
        bill_id: uuid.UUID,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Remove a document link from a bill. Restricted for approved bills if original invoice."""
        bill = await BillService.get_bill(db, org_id, bill_id)

        d_res = await db.execute(
            select(BillDocument)
            .where(BillDocument.id == document_id)
            .where(BillDocument.bill_id == bill_id)
            .where(BillDocument.organisation_id == org_id)
        )
        doc = d_res.scalar_one_or_none()
        if not doc:
            raise NotFoundError("Document not found on this bill.", code="DOCUMENT_NOT_FOUND")

        if bill.status in (BillStatus.APPROVED, BillStatus.AWAITING_PAYMENT, BillStatus.PAID) and doc.document_type == "ORIGINAL_INVOICE":
            raise BadRequestError("Cannot remove original invoice from an approved bill.", code="DOCUMENT_LOCKED")

        await db.delete(doc)
        await db.flush()

        await AuditService.log_static(
            db,
            action="BILL_DOCUMENT_REMOVED",
            resource_type="bill",
            resource_id=str(bill_id),
            organisation_id=org_id,
            user_id=user_id,
            diff={"document_id": str(document_id)},
        )

    # ── Workflow: Submit for Approval ────────────────────────
    @staticmethod
    async def submit_for_approval(
        db: AsyncSession,
        org_id: uuid.UUID,
        bill_id: uuid.UUID,
        user_id: uuid.UUID,
        comment: Optional[str] = None,
    ) -> Bill:
        """Transition DRAFT or REJECTED bill to AWAITING_APPROVAL."""
        bill = await BillService.get_bill(db, org_id, bill_id)

        if bill.status not in (BillStatus.DRAFT, BillStatus.REJECTED):
            raise BadRequestError(
                f"Only DRAFT or REJECTED bills can be submitted for approval. Current status: {bill.status.value}",
                code="INVALID_BILL_STATUS",
            )

        if not bill.lines:
            raise BadRequestError("Bill must contain at least one line item.", code="EMPTY_BILL")

        # Check required attachment policy if enabled in organisation settings
        setting_res = await db.execute(
            select(OrganisationSetting)
            .where(OrganisationSetting.organisation_id == org_id)
            .where(OrganisationSetting.key == "require_bill_attachment")
        )
        setting = setting_res.scalar_one_or_none()
        if setting and setting.value and setting.value.get("enabled", False):
            has_doc = any(d.document_type == "ORIGINAL_INVOICE" for d in bill.documents)
            if not has_doc and len(bill.documents) == 0:
                raise BadRequestError(
                    "Organisation policy requires an attached supplier invoice before submission.",
                    code="BILL_ATTACHMENT_REQUIRED",
                )

        bill.status = BillStatus.AWAITING_APPROVAL
        bill.submitted_for_approval_by_id = user_id
        bill.submitted_for_approval_at = datetime.now(UTC)

        event = BillApprovalEvent(
            organisation_id=org_id,
            bill_id=bill.id,
            actor_user_id=user_id,
            action=BillApprovalAction.SUBMITTED,
            comment=comment,
        )
        db.add(event)
        await db.flush()

        await AuditService.log_static(
            db,
            action="BILL_SUBMITTED",
            resource_type="bill",
            resource_id=str(bill.id),
            organisation_id=org_id,
            user_id=user_id,
            diff={"status": "AWAITING_APPROVAL", "comment": comment},
        )

        return await BillService.get_bill(db, org_id, bill.id)

    # ── Workflow: Approve Bill ───────────────────────────────
    @staticmethod
    async def approve_bill(
        db: AsyncSession,
        org_id: uuid.UUID,
        bill_id: uuid.UUID,
        user_id: uuid.UUID,
        comment: Optional[str] = None,
    ) -> Bill:
        """
        Approve an AWAITING_APPROVAL bill.
        Enforces separation of duties (optional self-approval block),
        creates immutable supplier snapshot, and transitions to APPROVED.
        """
        bill = await BillService.get_bill(db, org_id, bill_id)

        if bill.status != BillStatus.AWAITING_APPROVAL:
            raise BadRequestError(
                f"Only bills awaiting approval can be approved. Current status: {bill.status.value}",
                code="INVALID_BILL_STATUS",
            )

        # Check self-approval policy
        setting_res = await db.execute(
            select(OrganisationSetting)
            .where(OrganisationSetting.organisation_id == org_id)
            .where(OrganisationSetting.key == "allow_bill_self_approval")
        )
        setting = setting_res.scalar_one_or_none()
        if setting and setting.value and setting.value.get("enabled") is False:
            if bill.created_by_id == user_id:
                raise PermissionDeniedError(
                    "Separation of duties policy is active: Creators cannot approve their own bills.",
                )

        # Re-verify lines and snapshot supplier details
        supplier = bill.supplier
        if supplier:
            bill.supplier_name_snapshot = supplier.business_name
            bill.supplier_email_snapshot = supplier.email
            bill.supplier_vat_number_snapshot = supplier.vat_number

            # Address snapshot
            addr_res = await db.execute(
                select(ContactAddress)
                .where(ContactAddress.contact_id == supplier.id)
                .order_by(ContactAddress.is_primary.desc())
                .limit(1)
            )
            addr = addr_res.scalar_one_or_none()
            if addr:
                bill.supplier_address_snapshot = {
                    "line1": addr.line1,
                    "line2": addr.line2,
                    "city": addr.city,
                    "state": addr.county_region,
                    "postal_code": addr.postcode,
                    "country": addr.country_code,
                }

        bill.status = BillStatus.APPROVED
        bill.approved_by_id = user_id
        bill.approved_at = datetime.now(UTC)

        event = BillApprovalEvent(
            organisation_id=org_id,
            bill_id=bill.id,
            actor_user_id=user_id,
            action=BillApprovalAction.APPROVED,
            comment=comment,
        )
        db.add(event)
        await db.flush()

        await AuditService.log_static(
            db,
            action="BILL_APPROVED",
            resource_type="bill",
            resource_id=str(bill.id),
            organisation_id=org_id,
            user_id=user_id,
            diff={"status": "APPROVED", "total": str(bill.total), "comment": comment},
        )

        return await BillService.get_bill(db, org_id, bill.id)

    # ── Workflow: Reject Bill ────────────────────────────────
    @staticmethod
    async def reject_bill(
        db: AsyncSession,
        org_id: uuid.UUID,
        bill_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str,
    ) -> Bill:
        """Reject a bill awaiting approval. Reason is mandatory."""
        if not reason or not reason.strip():
            raise BadRequestError("Rejection reason is required.", code="REASON_REQUIRED")

        bill = await BillService.get_bill(db, org_id, bill_id)

        if bill.status != BillStatus.AWAITING_APPROVAL:
            raise BadRequestError(
                f"Only bills awaiting approval can be rejected. Current status: {bill.status.value}",
                code="INVALID_BILL_STATUS",
            )

        bill.status = BillStatus.REJECTED
        bill.rejected_by_id = user_id
        bill.rejected_at = datetime.now(UTC)
        bill.rejection_reason = reason.strip()

        event = BillApprovalEvent(
            organisation_id=org_id,
            bill_id=bill.id,
            actor_user_id=user_id,
            action=BillApprovalAction.REJECTED,
            comment=reason.strip(),
        )
        db.add(event)
        await db.flush()

        await AuditService.log_static(
            db,
            action="BILL_REJECTED",
            resource_type="bill",
            resource_id=str(bill.id),
            organisation_id=org_id,
            user_id=user_id,
            diff={"status": "REJECTED", "reason": reason.strip()},
        )

        return await BillService.get_bill(db, org_id, bill.id)

    # ── Workflow: Void Bill ──────────────────────────────────
    @staticmethod
    async def void_bill(
        db: AsyncSession,
        org_id: uuid.UUID,
        bill_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str,
    ) -> Bill:
        """Void an approved bill. Reason is required. Paid bills cannot be voided."""
        if not reason or not reason.strip():
            raise BadRequestError("Void reason is required.", code="REASON_REQUIRED")

        bill = await BillService.get_bill(db, org_id, bill_id)

        if bill.status in (BillStatus.DRAFT, BillStatus.VOID):
            if bill.status == BillStatus.DRAFT:
                raise BadRequestError("Delete DRAFT bills instead of voiding them.", code="INVALID_BILL_STATUS")
            raise BadRequestError("This bill is already void.", code="ALREADY_VOID")

        if bill.status == BillStatus.PAID or bill.amount_paid > Decimal("0"):
            raise BadRequestError(
                "Bills with payments cannot be voided directly. A supplier credit note must be recorded.",
                code="BILL_HAS_PAYMENTS",
            )

        bill.status = BillStatus.VOID
        bill.voided_by_id = user_id
        bill.voided_at = datetime.now(UTC)
        bill.void_reason = reason.strip()
        bill.amount_due = Decimal("0")

        await db.flush()

        await AuditService.log_static(
            db,
            action="BILL_VOIDED",
            resource_type="bill",
            resource_id=str(bill.id),
            organisation_id=org_id,
            user_id=user_id,
            diff={"status": "VOID", "reason": reason.strip()},
        )

        return await BillService.get_bill(db, org_id, bill.id)

    # ── Queries ──────────────────────────────────────────────
    @staticmethod
    async def get_bill(db: AsyncSession, org_id: uuid.UUID, bill_id: uuid.UUID) -> Bill:
        """Fetch a single bill with full relationships. Tenant-isolated."""
        result = await db.execute(
            select(Bill)
            .where(Bill.id == bill_id)
            .where(Bill.organisation_id == org_id)
            .options(
                selectinload(Bill.lines).selectinload(BillLine.tax_rate),
                selectinload(Bill.supplier),
                selectinload(Bill.documents).selectinload(BillDocument.file),
                selectinload(Bill.approval_events).selectinload(BillApprovalEvent.actor),
            )
        )
        bill = result.scalar_one_or_none()
        if not bill:
            raise NotFoundError("Supplier bill not found in this organisation.", code="BILL_NOT_FOUND")
        return bill

    @staticmethod
    async def list_bills(
        db: AsyncSession, org_id: uuid.UUID, filters: BillFilters
    ) -> dict:
        """List bills with filters, search, and pagination."""
        query = (
            select(Bill)
            .where(Bill.organisation_id == org_id)
            .options(
                selectinload(Bill.supplier),
                selectinload(Bill.lines),
            )
        )

        now = datetime.now(UTC)

        # Status filter
        if filters.status:
            status_upper = filters.status.upper()
            if status_upper == "OVERDUE":
                query = query.where(
                    Bill.status.in_([BillStatus.APPROVED, BillStatus.AWAITING_PAYMENT]),
                    Bill.amount_due > 0,
                    Bill.due_date < now,
                )
            elif status_upper == "AWAITING_PAYMENT":
                query = query.where(
                    Bill.status.in_([BillStatus.APPROVED, BillStatus.AWAITING_PAYMENT]),
                    Bill.amount_due > 0,
                    Bill.due_date >= now,
                )
            else:
                try:
                    status_enum = BillStatus(status_upper)
                    query = query.where(Bill.status == status_enum)
                except ValueError:
                    pass

        # Supplier filter
        if filters.supplier_id:
            query = query.where(Bill.supplier_id == filters.supplier_id)

        # Date range
        if filters.date_from:
            query = query.where(Bill.bill_date >= datetime.fromisoformat(filters.date_from))
        if filters.date_to:
            query = query.where(Bill.bill_date <= datetime.fromisoformat(filters.date_to))

        # Due date range
        if filters.due_date_from:
            query = query.where(Bill.due_date >= datetime.fromisoformat(filters.due_date_from))
        if filters.due_date_to:
            query = query.where(Bill.due_date <= datetime.fromisoformat(filters.due_date_to))

        # Currency
        if filters.currency:
            query = query.where(Bill.currency == filters.currency.upper())

        # Search across internal bill #, supplier invoice #, reference, PO #
        if filters.search:
            s_term = f"%{filters.search}%"
            query = query.where(
                or_(
                    Bill.internal_bill_number.ilike(s_term),
                    Bill.supplier_invoice_number.ilike(s_term),
                    Bill.supplier_reference.ilike(s_term),
                    Bill.purchase_order_reference.ilike(s_term),
                    Bill.supplier_name_snapshot.ilike(s_term),
                )
            )

        # Total count
        count_q = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_q)
        total = total_result.scalar_one()

        # Ordering
        sort_col = getattr(Bill, filters.sort_by, Bill.bill_date)
        if filters.sort_dir.lower() == "desc":
            query = query.order_by(desc(sort_col))
        else:
            query = query.order_by(sort_col)

        # Pagination
        offset = (filters.page - 1) * filters.page_size
        query = query.offset(offset).limit(filters.page_size)

        result = await db.execute(query)
        bills = result.scalars().all()

        total_pages = (total + filters.page_size - 1) // filters.page_size if total > 0 else 1

        return {
            "items": bills,
            "total": total,
            "page": filters.page,
            "page_size": filters.page_size,
            "total_pages": total_pages,
        }

    # ── Purchases Metrics ────────────────────────────────────
    @staticmethod
    async def get_purchases_metrics(
        db: AsyncSession, org_id: uuid.UUID
    ) -> PurchasesMetricsResponse:
        """Aggregates metrics for the purchases dashboard."""
        now = datetime.now(UTC)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # All bills for org
        result = await db.execute(
            select(Bill)
            .where(Bill.organisation_id == org_id)
            .where(Bill.status != BillStatus.VOID)
        )
        bills = result.scalars().all()

        awaiting_app_count = 0
        awaiting_app_amt = Decimal("0")
        awaiting_pay_count = 0
        awaiting_pay_amt = Decimal("0")
        overdue_count = 0
        overdue_amt = Decimal("0")
        this_month_count = 0
        this_month_amt = Decimal("0")

        for b in bills:
            # Month to date
            b_date = b.bill_date
            if b_date.tzinfo is None:
                b_date = b_date.replace(tzinfo=UTC)
            if b_date >= start_of_month:
                this_month_count += 1
                this_month_amt += Decimal(str(b.total))

            # Awaiting approval
            if b.status == BillStatus.AWAITING_APPROVAL:
                awaiting_app_count += 1
                awaiting_app_amt += Decimal(str(b.total))

            # Approved / Awaiting Payment or Overdue
            if b.status in (BillStatus.APPROVED, BillStatus.AWAITING_PAYMENT):
                due = b.due_date
                if due.tzinfo is None:
                    due = due.replace(tzinfo=UTC)
                if b.amount_due > 0 and now > due:
                    overdue_count += 1
                    overdue_amt += Decimal(str(b.amount_due))
                elif b.amount_due > 0:
                    awaiting_pay_count += 1
                    awaiting_pay_amt += Decimal(str(b.amount_due))

        return PurchasesMetricsResponse(
            awaiting_approval_count=awaiting_app_count,
            awaiting_approval_amount=awaiting_app_amt,
            awaiting_payment_count=awaiting_pay_count,
            awaiting_payment_amount=awaiting_pay_amt,
            overdue_count=overdue_count,
            overdue_amount=overdue_amt,
            this_month_count=this_month_count,
            this_month_amount=this_month_amt,
        )
