"""
Warp Ladger — Invoice Service
Full business logic for invoice lifecycle management.

Key rules enforced here:
- All financial totals recalculated server-side (frontend totals ignored)
- Decimal arithmetic throughout (no float)
- Approval is atomic (transaction wraps: validate → number → snapshot → status → audit)
- Approved invoices are protected from uncontrolled edits
- Cross-tenant isolation on every query
- OVERDUE status derived at read time (not stored)
"""
import math
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.audit.service import AuditService
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.database.models import (
    Contact,
    ContactAddress,
    ContactStatus,
    ContactType,
    Invoice,
    InvoiceDelivery,
    InvoiceLine,
    InvoiceStatus,
    PaymentTerm,
    TaxRate,
    User,
)
from app.invoices.money_service import LineCalcResult, MoneyService
from app.invoices.schemas import (
    InvoiceCreate,
    InvoiceFilters,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceUpdate,
)
from app.invoices.sequence_service import SequenceService

log = structlog.get_logger(__name__)

EDITABLE_STATUSES = {InvoiceStatus.DRAFT}


class InvoiceService:
    """Complete invoice lifecycle management service."""

    # ── Helpers ──────────────────────────────────────────────
    @staticmethod
    def _effective_status(invoice: Invoice) -> str:
        """
        Derive the effective display status.
        OVERDUE is computed, not stored, to prevent inconsistency.
        """
        if invoice.status in (InvoiceStatus.APPROVED, InvoiceStatus.SENT,
                               InvoiceStatus.AWAITING_PAYMENT):
            due = invoice.due_date
            now = datetime.now(UTC)
            # Make both timezone-aware for comparison
            if due.tzinfo is None:
                due = due.replace(tzinfo=UTC)
            if now > due and Decimal(str(invoice.amount_due)) > Decimal("0"):
                return "OVERDUE"
        return invoice.status.value

    @staticmethod
    async def _load_invoice(
        db: AsyncSession,
        org_id: uuid.UUID,
        invoice_id: uuid.UUID,
        with_lines: bool = False,
    ) -> Invoice:
        """Load invoice and verify org ownership. Returns 404 for wrong org (no info leak)."""
        query = (
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .where(Invoice.organisation_id == org_id)
        )
        if with_lines:
            query = query.options(selectinload(Invoice.lines))
        result = await db.execute(query)
        invoice = result.scalar_one_or_none()
        if invoice is None:
            raise NotFoundError("Invoice not found.")
        return invoice

    @staticmethod
    async def _resolve_customer(
        db: AsyncSession,
        org_id: uuid.UUID,
        customer_id: uuid.UUID,
    ) -> Contact:
        """Verify customer exists, belongs to org, and is a customer-type contact."""
        result = await db.execute(
            select(Contact)
            .options(selectinload(Contact.addresses))
            .where(Contact.id == customer_id)
            .where(Contact.organisation_id == org_id)
            .where(Contact.status == ContactStatus.ACTIVE)
            .where(Contact.deleted_at.is_(None))
        )
        customer = result.scalar_one_or_none()
        if customer is None:
            raise NotFoundError("Customer not found in this organisation.")
        if customer.contact_type not in (ContactType.CUSTOMER, ContactType.BOTH):
            raise BadRequestError("Selected contact is not a customer.")
        return customer

    @staticmethod
    async def _resolve_tax_rate(
        db: AsyncSession,
        org_id: uuid.UUID,
        tax_rate_id: Optional[uuid.UUID],
    ) -> Optional[TaxRate]:
        if tax_rate_id is None:
            return None
        result = await db.execute(
            select(TaxRate)
            .where(TaxRate.id == tax_rate_id)
            .where(TaxRate.organisation_id == org_id)
            .where(TaxRate.active.is_(True))
        )
        tax_rate = result.scalar_one_or_none()
        if tax_rate is None:
            raise BadRequestError(f"Tax rate {tax_rate_id} not found or inactive.")
        return tax_rate

    @staticmethod
    def _build_line_snapshot(
        db_line: InvoiceLine,
        result: LineCalcResult,
        tax_rate: Optional[TaxRate],
    ) -> None:
        """Apply computed values back onto the ORM line object."""
        db_line.net_amount = result.net_amount
        db_line.tax_amount = result.tax_amount
        db_line.gross_amount = result.gross_amount
        db_line.discount_amount = result.discount_amount
        db_line.tax_rate_snapshot = tax_rate.rate if tax_rate else Decimal("0")

    @staticmethod
    def _build_customer_snapshot(customer: Contact) -> dict:
        """Extract billing address into a stable JSON snapshot."""
        billing = None
        for addr in (customer.addresses or []):
            if addr.address_type.value == "BILLING" and addr.is_primary:
                billing = {
                    "line1": addr.line1,
                    "line2": addr.line2,
                    "city": addr.city,
                    "county_region": addr.county_region,
                    "postcode": addr.postcode,
                    "country_code": addr.country_code,
                }
                break
        return billing or {}

    # ── Create Draft ─────────────────────────────────────────
    @staticmethod
    async def create_draft(
        db: AsyncSession,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        data: InvoiceCreate,
    ) -> Invoice:
        """Create a new DRAFT invoice with backend-calculated totals."""
        customer = await InvoiceService._resolve_customer(db, org_id, data.customer_id)

        # Build and calculate all lines
        calc_lines: list[LineCalcResult] = []
        db_lines: list[InvoiceLine] = []
        for idx, line_data in enumerate(data.lines):
            tax_rate = await InvoiceService._resolve_tax_rate(
                db, org_id, line_data.tax_rate_id
            )
            rate = tax_rate.rate if tax_rate else Decimal("0")
            result = MoneyService.calculate_line(
                quantity=line_data.quantity,
                unit_price=line_data.unit_price,
                tax_rate=rate,
                discount_type=line_data.discount_type.value if line_data.discount_type else None,
                discount_value=line_data.discount_value,
            )
            calc_lines.append(result)
            db_line = InvoiceLine(
                organisation_id=org_id,
                position=line_data.position if line_data.position else idx,
                description=line_data.description,
                quantity=result.quantity,
                unit_price=result.unit_price,
                discount_type=line_data.discount_type,
                discount_value=result.discount_value,
                net_amount=result.net_amount,
                tax_amount=result.tax_amount,
                gross_amount=result.gross_amount,
                tax_rate_id=line_data.tax_rate_id,
                tax_rate_snapshot=tax_rate.rate if tax_rate else Decimal("0"),
            )
            db_lines.append(db_line)

        totals = MoneyService.calculate_invoice_totals(calc_lines)

        invoice = Invoice(
            organisation_id=org_id,
            customer_id=data.customer_id,
            status=InvoiceStatus.DRAFT,
            issue_date=data.issue_date,
            due_date=data.due_date,
            currency=data.currency,
            payment_terms_id=data.payment_terms_id,
            customer_reference=data.customer_reference,
            purchase_order_reference=data.purchase_order_reference,
            notes=data.notes,
            terms=data.terms,
            internal_notes=data.internal_notes,
            subtotal=totals.subtotal,
            discount_total=totals.discount_total,
            tax_total=totals.tax_total,
            total=totals.total,
            amount_paid=Decimal("0"),
            amount_due=totals.total,
            created_by_id=user_id,
        )
        db.add(invoice)
        await db.flush()

        for db_line in db_lines:
            db_line.invoice_id = invoice.id
            db.add(db_line)

        await db.flush()

        await AuditService.log_static(
            db,
            action="INVOICE_CREATED",
            resource_type="invoice",
            resource_id=str(invoice.id),
            organisation_id=org_id,
            user_id=user_id,
            diff={"status": "DRAFT", "total": str(totals.total)},
        )

        log.info("invoice_draft_created", invoice_id=str(invoice.id), org_id=str(org_id))
        return await InvoiceService.get_invoice(db, org_id, invoice.id)

    # ── Update Draft ─────────────────────────────────────────
    @staticmethod
    async def update_draft(
        db: AsyncSession,
        org_id: uuid.UUID,
        invoice_id: uuid.UUID,
        user_id: uuid.UUID,
        data: InvoiceUpdate,
    ) -> Invoice:
        """Update a DRAFT invoice. Raises if invoice is not editable."""
        invoice = await InvoiceService._load_invoice(db, org_id, invoice_id, with_lines=True)

        if invoice.status not in EDITABLE_STATUSES:
            raise BadRequestError(
                "Only DRAFT invoices can be edited directly. "
                "To modify an approved invoice, use void or credit note processes.",
                code="INVOICE_NOT_EDITABLE",
            )

        # Update scalar fields if provided
        update_fields = data.model_dump(exclude_none=True, exclude={"lines"})
        old_values = {}
        for key, val in update_fields.items():
            old_values[key] = getattr(invoice, key, None)
            setattr(invoice, key, val)

        # Rebuild lines if provided
        if data.lines is not None:
            # Remove existing lines
            for existing in invoice.lines:
                await db.delete(existing)
            await db.flush()

            calc_lines: list[LineCalcResult] = []
            for idx, line_data in enumerate(data.lines):
                tax_rate = await InvoiceService._resolve_tax_rate(
                    db, org_id, line_data.tax_rate_id
                )
                rate = tax_rate.rate if tax_rate else Decimal("0")
                result = MoneyService.calculate_line(
                    quantity=line_data.quantity,
                    unit_price=line_data.unit_price,
                    tax_rate=rate,
                    discount_type=line_data.discount_type.value if line_data.discount_type else None,
                    discount_value=line_data.discount_value,
                )
                calc_lines.append(result)
                new_line = InvoiceLine(
                    organisation_id=org_id,
                    invoice_id=invoice.id,
                    position=line_data.position if line_data.position else idx,
                    description=line_data.description,
                    quantity=result.quantity,
                    unit_price=result.unit_price,
                    discount_type=line_data.discount_type,
                    discount_value=result.discount_value,
                    net_amount=result.net_amount,
                    tax_amount=result.tax_amount,
                    gross_amount=result.gross_amount,
                    tax_rate_id=line_data.tax_rate_id,
                    tax_rate_snapshot=tax_rate.rate if tax_rate else Decimal("0"),
                )
                db.add(new_line)

            totals = MoneyService.calculate_invoice_totals(calc_lines)
            invoice.subtotal = totals.subtotal
            invoice.discount_total = totals.discount_total
            invoice.tax_total = totals.tax_total
            invoice.total = totals.total
            invoice.amount_due = totals.total - invoice.amount_paid

        await db.flush()
        await AuditService.log_static(
            db,
            action="INVOICE_UPDATED",
            resource_type="invoice",
            resource_id=str(invoice.id),
            organisation_id=org_id,
            user_id=user_id,
            diff={"changed_fields": list(update_fields.keys())},
        )
        return await InvoiceService.get_invoice(db, org_id, invoice.id)

    # ── Delete Draft ─────────────────────────────────────────
    @staticmethod
    async def delete_draft(
        db: AsyncSession,
        org_id: uuid.UUID,
        invoice_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Hard-delete a DRAFT invoice. Approved invoices must be voided instead."""
        invoice = await InvoiceService._load_invoice(db, org_id, invoice_id)
        if invoice.status != InvoiceStatus.DRAFT:
            raise BadRequestError("Only DRAFT invoices can be deleted.", code="INVOICE_NOT_EDITABLE")
        await db.delete(invoice)
        await db.flush()
        await AuditService.log_static(
            db,
            action="INVOICE_DELETED",
            resource_type="invoice",
            resource_id=str(invoice_id),
            organisation_id=org_id,
            user_id=user_id,
        )

    # ── Approve Invoice ───────────────────────────────────────
    @staticmethod
    async def approve_invoice(
        db: AsyncSession,
        org_id: uuid.UUID,
        invoice_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Invoice:
        """
        Approve a draft invoice. This is an atomic operation:
        1. Validate draft + lines
        2. Re-verify all calculations
        3. Generate unique invoice number (row-locked)
        4. Capture customer snapshot
        5. Transition status to APPROVED
        6. Record approver + timestamp
        7. Audit log

        All within a single DB transaction — caller must commit.
        """
        invoice = await InvoiceService._load_invoice(db, org_id, invoice_id, with_lines=True)

        # ── Validation ────────────────────────────────────────
        if invoice.status != InvoiceStatus.DRAFT:
            raise BadRequestError(
                "Only DRAFT invoices can be approved.",
                code="INVALID_INVOICE_STATUS",
            )
        if not invoice.lines:
            raise BadRequestError("Invoice must have at least one line item.")
        if not invoice.customer_id:
            raise BadRequestError("Invoice must have a customer.")

        # Verify customer still exists and belongs to org
        customer = await InvoiceService._resolve_customer(db, org_id, invoice.customer_id)

        # Re-verify all financial calculations server-side
        recalc_lines: list[LineCalcResult] = []
        for line in invoice.lines:
            rate = line.tax_rate_snapshot if line.tax_rate_snapshot else Decimal("0")
            result = MoneyService.calculate_line(
                quantity=line.quantity,
                unit_price=line.unit_price,
                tax_rate=rate,
                discount_type=line.discount_type.value if line.discount_type else None,
                discount_value=line.discount_value,
            )
            recalc_lines.append(result)

        recalc_totals = MoneyService.calculate_invoice_totals(recalc_lines)

        # ── Generate invoice number (row-locked) ──────────────
        invoice_number = await SequenceService.generate_invoice_number(db, org_id)

        # ── Customer snapshot ─────────────────────────────────
        billing_snapshot = InvoiceService._build_customer_snapshot(customer)
        invoice.customer_name_snapshot = (
            customer.legal_name or customer.business_name
        )
        invoice.customer_email_snapshot = customer.email
        invoice.customer_vat_number_snapshot = customer.vat_number
        invoice.billing_address_snapshot = billing_snapshot

        # ── Update invoice with verified totals ───────────────
        invoice.subtotal = recalc_totals.subtotal
        invoice.discount_total = recalc_totals.discount_total
        invoice.tax_total = recalc_totals.tax_total
        invoice.total = recalc_totals.total
        invoice.amount_paid = Decimal("0")
        invoice.amount_due = recalc_totals.total

        # ── Transition ────────────────────────────────────────
        invoice.invoice_number = invoice_number
        invoice.status = InvoiceStatus.APPROVED
        invoice.approved_by_id = user_id
        invoice.approved_at = datetime.now(UTC)

        await db.flush()

        await AuditService.log_static(
            db,
            action="INVOICE_APPROVED",
            resource_type="invoice",
            resource_id=str(invoice.id),
            organisation_id=org_id,
            user_id=user_id,
            diff={
                "invoice_number": invoice_number,
                "total": str(recalc_totals.total),
                "status": "APPROVED",
            },
        )

        log.info(
            "invoice_approved",
            invoice_id=str(invoice.id),
            invoice_number=invoice_number,
            org_id=str(org_id),
        )
        return await InvoiceService.get_invoice(db, org_id, invoice.id)

    # ── Void Invoice ──────────────────────────────────────────
    @staticmethod
    async def void_invoice(
        db: AsyncSession,
        org_id: uuid.UUID,
        invoice_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str,
    ) -> Invoice:
        """
        Void an approved invoice. DRAFT invoices should be deleted instead.
        Voided invoices are never hard-deleted — they remain for audit purposes.
        """
        invoice = await InvoiceService._load_invoice(db, org_id, invoice_id)

        if invoice.status in (InvoiceStatus.DRAFT, InvoiceStatus.VOID):
            if invoice.status == InvoiceStatus.DRAFT:
                raise BadRequestError("Delete DRAFT invoices instead of voiding them.")
            raise BadRequestError("Invoice is already void.")

        if invoice.status == InvoiceStatus.PAID:
            raise BadRequestError(
                "Paid invoices cannot be voided. Issue a credit note instead.",
                code="INVALID_INVOICE_STATUS",
            )

        invoice.status = InvoiceStatus.VOID
        invoice.voided_by_id = user_id
        invoice.voided_at = datetime.now(UTC)
        invoice.void_reason = reason

        await db.flush()
        await AuditService.log_static(
            db,
            action="INVOICE_VOIDED",
            resource_type="invoice",
            resource_id=str(invoice.id),
            organisation_id=org_id,
            user_id=user_id,
            diff={"void_reason": reason, "status": "VOID"},
        )
        return await InvoiceService.get_invoice(db, org_id, invoice.id)

    # ── Get Single Invoice ────────────────────────────────────
    @staticmethod
    async def get_invoice(
        db: AsyncSession,
        org_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> Invoice:
        query = (
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .where(Invoice.organisation_id == org_id)
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.deliveries),
            )
        )
        result = await db.execute(query)
        invoice = result.scalar_one_or_none()
        if invoice is None:
            raise NotFoundError("Invoice not found.")
        return invoice

    # ── List Invoices ─────────────────────────────────────────
    @staticmethod
    async def list_invoices(
        db: AsyncSession,
        org_id: uuid.UUID,
        filters: InvoiceFilters,
    ) -> dict:
        """Paginated, filtered, sorted invoice list with OVERDUE derivation."""
        query = select(Invoice).where(Invoice.organisation_id == org_id)

        now = datetime.now(UTC)

        # Status filter — OVERDUE is special (derived)
        if filters.status:
            if filters.status.upper() == "OVERDUE":
                query = query.where(
                    Invoice.status.in_([
                        InvoiceStatus.APPROVED,
                        InvoiceStatus.SENT,
                        InvoiceStatus.AWAITING_PAYMENT,
                    ])
                ).where(Invoice.due_date < now).where(Invoice.amount_due > 0)
            else:
                try:
                    status_enum = InvoiceStatus(filters.status.upper())
                    query = query.where(Invoice.status == status_enum)
                except ValueError:
                    pass

        if filters.customer_id:
            query = query.where(Invoice.customer_id == filters.customer_id)
        if filters.date_from:
            query = query.where(Invoice.issue_date >= filters.date_from)
        if filters.date_to:
            query = query.where(Invoice.issue_date <= filters.date_to)
        if filters.currency:
            query = query.where(Invoice.currency == filters.currency.upper())
        if filters.search:
            s = f"%{filters.search}%"
            query = query.where(
                or_(
                    Invoice.invoice_number.ilike(s),
                    Invoice.customer_name_snapshot.ilike(s),
                    Invoice.customer_reference.ilike(s),
                    Invoice.purchase_order_reference.ilike(s),
                )
            )

        # Count
        count_result = await db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        # Sort
        sort_col = getattr(Invoice, filters.sort_by, Invoice.created_at)
        if filters.sort_dir == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        # Paginate
        offset = (filters.page - 1) * filters.page_size
        query = query.offset(offset).limit(filters.page_size)

        result = await db.execute(query)
        invoices = result.scalars().all()

        return {
            "items": invoices,
            "total": total,
            "page": filters.page,
            "page_size": filters.page_size,
            "total_pages": math.ceil(total / filters.page_size) if total else 1,
        }

    # ── Mark Sent ─────────────────────────────────────────────
    @staticmethod
    async def mark_sent(
        db: AsyncSession,
        org_id: uuid.UUID,
        invoice_id: uuid.UUID,
        recipient_email: str,
        cc: Optional[str],
        subject: str,
        sent_by_id: uuid.UUID,
    ) -> InvoiceDelivery:
        """Create a delivery record and update invoice.sent_at."""
        invoice = await InvoiceService._load_invoice(db, org_id, invoice_id)

        if invoice.status == InvoiceStatus.DRAFT:
            raise BadRequestError("Approve the invoice before sending.", code="INVALID_INVOICE_STATUS")
        if invoice.status == InvoiceStatus.VOID:
            raise BadRequestError("Cannot send a voided invoice.", code="INVALID_INVOICE_STATUS")

        delivery = InvoiceDelivery(
            organisation_id=org_id,
            invoice_id=invoice_id,
            recipient_email=recipient_email,
            cc=cc,
            subject=subject,
            status="QUEUED",
            sent_by_id=sent_by_id,
        )
        db.add(delivery)

        # Update invoice status to SENT/AWAITING_PAYMENT
        if invoice.status == InvoiceStatus.APPROVED:
            invoice.status = InvoiceStatus.SENT
            invoice.sent_at = datetime.now(UTC)

        await db.flush()
        await AuditService.log_static(
            db,
            action="INVOICE_SENT",
            resource_type="invoice",
            resource_id=str(invoice_id),
            organisation_id=org_id,
            user_id=sent_by_id,
            diff={"recipient_email": recipient_email},
        )
        await db.refresh(delivery)
        return delivery
