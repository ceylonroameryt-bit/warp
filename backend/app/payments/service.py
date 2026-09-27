"""
Warp Ladger — Payments & Allocations Service Layer (Phase 6)
Enforces multi-tenancy, row-locking concurrency, exact Decimal financial arithmetic,
and double-entry integrity on payment allocations and balance rollbacks.
"""
from datetime import UTC, datetime
from decimal import Decimal
import math
from typing import Optional
import uuid

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.audit.service import AuditService
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError, ValidationFailedError
from app.database.models import (
    AllocationTargetType,
    BankAccount,
    BankAccountType,
    Bill,
    BillStatus,
    Contact,
    Invoice,
    InvoiceStatus,
    OrganisationPaymentSequence,
    Payment,
    PaymentAllocation,
    PaymentMethod,
    PaymentStatus,
    PaymentType,
)
from app.payments.schemas import (
    BankAccountCreate,
    BankAccountResponse,
    BankAccountUpdate,
    PaymentAllocateRequest,
    PaymentAllocationResponse,
    PaymentCreate,
    PaymentDetailResponse,
    PaymentMetricsResponse,
    PaymentResponse,
)

log = structlog.get_logger(__name__)


class PaymentSequenceService:
    """Manages contiguous, concurrency-safe payment number counters using FOR UPDATE row locks."""

    @staticmethod
    async def get_next_payment_number(
        db: AsyncSession,
        org_id: uuid.UUID,
        payment_type: PaymentType,
    ) -> str:
        prefix = "PAY-"
        stmt = (
            select(OrganisationPaymentSequence)
            .where(
                OrganisationPaymentSequence.organisation_id == org_id,
                OrganisationPaymentSequence.payment_type == payment_type,
            )
            .with_for_update()
        )
        result = await db.execute(stmt)
        seq = result.scalar_one_or_none()

        if seq is None:
            seq = OrganisationPaymentSequence(
                organisation_id=org_id,
                payment_type=payment_type,
                next_number=1,
                prefix=prefix,
            )
            db.add(seq)
            await db.flush()

        current_num = seq.next_number
        seq.next_number += 1
        await db.flush()

        return f"{seq.prefix}{current_num:06d}"


class PaymentService:
    """Core payment processing and allocation engine."""

    # ─── Bank Accounts ───────────────────────────────────────────
    @staticmethod
    async def create_bank_account(
        db: AsyncSession,
        org_id: uuid.UUID,
        payload: BankAccountCreate,
        user_id: uuid.UUID,
    ) -> BankAccountResponse:
        # Check duplicate name in org
        existing = await db.execute(
            select(BankAccount).where(
                BankAccount.organisation_id == org_id,
                BankAccount.account_name == payload.account_name,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Bank account '{payload.account_name}' already exists.")

        if payload.is_default:
            # Clear other defaults
            all_accounts = await db.execute(
                select(BankAccount).where(BankAccount.organisation_id == org_id)
            )
            for acc in all_accounts.scalars().all():
                acc.is_default = False

        account = BankAccount(
            organisation_id=org_id,
            account_name=payload.account_name,
            account_type=payload.account_type,
            currency=payload.currency.upper(),
            account_number=payload.account_number,
            sort_code=payload.sort_code,
            iban=payload.iban,
            bic_swift=payload.bic_swift,
            opening_balance=payload.opening_balance,
            current_balance=payload.opening_balance,
            is_default=payload.is_default,
            active=True,
        )
        db.add(account)
        await db.flush()

        await AuditService.log_static(
            db=db,
            action="BANK_ACCOUNT_CREATED",
            resource_type="bank_account",
            resource_id=str(account.id),
            organisation_id=org_id,
            user_id=user_id,
            diff={"account_name": account.account_name, "currency": account.currency},
        )
        await db.flush()
        return BankAccountResponse.model_validate(account)

    @staticmethod
    async def list_bank_accounts(
        db: AsyncSession,
        org_id: uuid.UUID,
    ) -> list[BankAccountResponse]:
        result = await db.execute(
            select(BankAccount)
            .where(BankAccount.organisation_id == org_id, BankAccount.active == True)
            .order_by(BankAccount.is_default.desc(), BankAccount.account_name)
        )
        return [BankAccountResponse.model_validate(a) for a in result.scalars().all()]

    @staticmethod
    async def get_bank_account(
        db: AsyncSession,
        org_id: uuid.UUID,
        account_id: uuid.UUID,
    ) -> BankAccountResponse:
        result = await db.execute(
            select(BankAccount).where(
                BankAccount.id == account_id,
                BankAccount.organisation_id == org_id,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise NotFoundError("Bank account not found.")
        return BankAccountResponse.model_validate(account)

    # ─── Payments ────────────────────────────────────────────────
    @staticmethod
    async def record_payment(
        db: AsyncSession,
        org_id: uuid.UUID,
        payload: PaymentCreate,
        user_id: uuid.UUID,
    ) -> PaymentDetailResponse:
        # 1. Contact validation
        contact = None
        if payload.contact_id:
            c_res = await db.execute(
                select(Contact).where(
                    Contact.id == payload.contact_id,
                    Contact.organisation_id == org_id,
                )
            )
            contact = c_res.scalar_one_or_none()
            if not contact:
                raise NotFoundError("Contact not found in organisation.")

        # 2. Bank account validation
        bank_account = None
        if payload.bank_account_id:
            ba_res = await db.execute(
                select(BankAccount).where(
                    BankAccount.id == payload.bank_account_id,
                    BankAccount.organisation_id == org_id,
                )
            )
            bank_account = ba_res.scalar_one_or_none()
            if not bank_account:
                raise NotFoundError("Bank account not found in organisation.")

        # 3. Generate sequential number
        payment_num = await PaymentSequenceService.get_next_payment_number(
            db, org_id, payload.payment_type
        )

        payment_dt = payload.payment_date or datetime.now(UTC)

        payment = Payment(
            organisation_id=org_id,
            payment_number=payment_num,
            payment_type=payload.payment_type,
            status=PaymentStatus.POSTED,
            contact_id=payload.contact_id,
            bank_account_id=payload.bank_account_id,
            payment_date=payment_dt,
            amount=payload.amount,
            currency=payload.currency.upper(),
            payment_method=payload.payment_method,
            reference=payload.reference,
            allocated_amount=Decimal("0.0000"),
            unallocated_amount=payload.amount,
            notes=payload.notes,
            created_by_id=user_id,
        )
        db.add(payment)
        await db.flush()

        # 4. Process inline allocations if provided
        total_allocated = Decimal("0.0000")
        allocation_responses: list[PaymentAllocationResponse] = []

        if payload.allocations:
            for alloc_item in payload.allocations:
                if alloc_item.amount <= Decimal("0.0000"):
                    raise ValidationFailedError("Allocation amount must be greater than zero.")

                target_number = None

                if alloc_item.target_type == AllocationTargetType.INVOICE:
                    if not alloc_item.invoice_id:
                        raise ValidationFailedError("invoice_id is required for INVOICE allocation.")

                    # Row lock the invoice
                    inv_res = await db.execute(
                        select(Invoice)
                        .where(
                            Invoice.id == alloc_item.invoice_id,
                            Invoice.organisation_id == org_id,
                        )
                        .with_for_update()
                    )
                    inv = inv_res.scalar_one_or_none()
                    if not inv:
                        raise NotFoundError("Invoice not found in organisation.")

                    if inv.status in (InvoiceStatus.DRAFT, InvoiceStatus.VOID):
                        raise ValidationFailedError(
                            f"Cannot allocate payment to invoice in status '{inv.status.value}'."
                        )

                    if alloc_item.amount > inv.amount_due:
                        raise ValidationFailedError(
                            f"Allocation amount ({alloc_item.amount}) exceeds invoice balance due ({inv.amount_due})."
                        )

                    # Update invoice financials
                    inv.amount_paid += alloc_item.amount
                    inv.amount_due = inv.total - inv.amount_paid
                    if inv.amount_due == Decimal("0.0000"):
                        inv.status = InvoiceStatus.PAID
                    else:
                        inv.status = InvoiceStatus.PARTIALLY_PAID

                    target_number = inv.invoice_number

                elif alloc_item.target_type == AllocationTargetType.BILL:
                    if not alloc_item.bill_id:
                        raise ValidationFailedError("bill_id is required for BILL allocation.")

                    # Row lock the bill
                    bill_res = await db.execute(
                        select(Bill)
                        .where(
                            Bill.id == alloc_item.bill_id,
                            Bill.organisation_id == org_id,
                        )
                        .with_for_update()
                    )
                    bill = bill_res.scalar_one_or_none()
                    if not bill:
                        raise NotFoundError("Supplier bill not found in organisation.")

                    if bill.status in (BillStatus.DRAFT, BillStatus.AWAITING_APPROVAL, BillStatus.REJECTED, BillStatus.VOID):
                        raise ValidationFailedError(
                            f"Cannot allocate payment to bill in status '{bill.status.value}'."
                        )

                    if alloc_item.amount > bill.amount_due:
                        raise ValidationFailedError(
                            f"Allocation amount ({alloc_item.amount}) exceeds bill balance due ({bill.amount_due})."
                        )

                    # Update bill financials
                    bill.amount_paid += alloc_item.amount
                    bill.amount_due = bill.total - bill.amount_paid
                    if bill.amount_due == Decimal("0.0000"):
                        bill.status = BillStatus.PAID
                    else:
                        bill.status = BillStatus.PARTIALLY_PAID

                    target_number = bill.internal_bill_number

                total_allocated += alloc_item.amount

                alloc_rec = PaymentAllocation(
                    organisation_id=org_id,
                    payment_id=payment.id,
                    target_type=alloc_item.target_type,
                    invoice_id=alloc_item.invoice_id,
                    bill_id=alloc_item.bill_id,
                    amount=alloc_item.amount,
                    allocated_at=datetime.now(UTC),
                    allocated_by_id=user_id,
                    notes=alloc_item.notes,
                )
                db.add(alloc_rec)
                await db.flush()

                allocation_responses.append(
                    PaymentAllocationResponse(
                        id=alloc_rec.id,
                        organisation_id=org_id,
                        payment_id=payment.id,
                        target_type=alloc_rec.target_type,
                        invoice_id=alloc_rec.invoice_id,
                        bill_id=alloc_rec.bill_id,
                        target_number=target_number,
                        amount=alloc_rec.amount,
                        allocated_at=alloc_rec.allocated_at,
                        allocated_by_id=alloc_rec.allocated_by_id,
                        notes=alloc_rec.notes,
                    )
                )

        if total_allocated > payment.amount:
            raise ValidationFailedError(
                f"Total allocated ({total_allocated}) cannot exceed payment amount ({payment.amount})."
            )

        payment.allocated_amount = total_allocated
        payment.unallocated_amount = payment.amount - total_allocated

        # 5. Update bank account balance if specified
        if bank_account:
            if payment.payment_type == PaymentType.INCOMING:
                bank_account.current_balance += payment.amount
            elif payment.payment_type == PaymentType.OUTGOING:
                bank_account.current_balance -= payment.amount

        # 6. Audit event
        await AuditService.log_static(
            db=db,
            action="PAYMENT_RECORDED",
            resource_type="payment",
            resource_id=str(payment.id),
            organisation_id=org_id,
            user_id=user_id,
            diff={
                "payment_number": payment.payment_number,
                "amount": str(payment.amount),
                "type": payment.payment_type.value,
                "allocated": str(payment.allocated_amount),
                "unallocated": str(payment.unallocated_amount),
            },
        )
        await db.flush()

        return PaymentDetailResponse(
            id=payment.id,
            organisation_id=payment.organisation_id,
            payment_number=payment.payment_number,
            payment_type=payment.payment_type,
            status=payment.status,
            contact_id=payment.contact_id,
            contact_name=contact.business_name if contact else None,
            bank_account_id=payment.bank_account_id,
            bank_account_name=bank_account.account_name if bank_account else None,
            payment_date=payment.payment_date,
            amount=payment.amount,
            currency=payment.currency,
            payment_method=payment.payment_method,
            reference=payment.reference,
            allocated_amount=payment.allocated_amount,
            unallocated_amount=payment.unallocated_amount,
            notes=payment.notes,
            created_by_id=payment.created_by_id,
            voided_by_id=payment.voided_by_id,
            voided_at=payment.voided_at,
            void_reason=payment.void_reason,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
            allocations=allocation_responses,
        )

    @staticmethod
    async def allocate_payment(
        db: AsyncSession,
        org_id: uuid.UUID,
        payment_id: uuid.UUID,
        payload: PaymentAllocateRequest,
        user_id: uuid.UUID,
    ) -> PaymentDetailResponse:
        # Load payment with row lock
        p_res = await db.execute(
            select(Payment)
            .where(Payment.id == payment_id, Payment.organisation_id == org_id)
            .options(selectinload(Payment.allocations))
            .with_for_update()
        )
        payment = p_res.scalar_one_or_none()
        if not payment:
            raise NotFoundError("Payment not found in organisation.")

        if payment.status != PaymentStatus.POSTED:
            raise ValidationFailedError(f"Cannot allocate payment with status '{payment.status.value}'.")

        add_alloc_total = sum(item.amount for item in payload.allocations)
        if add_alloc_total > payment.unallocated_amount:
            raise ValidationFailedError(
                f"Requested allocation ({add_alloc_total}) exceeds unallocated funds ({payment.unallocated_amount})."
            )

        for alloc_item in payload.allocations:
            if alloc_item.amount <= Decimal("0.0000"):
                raise ValidationFailedError("Allocation amount must be greater than zero.")

            if alloc_item.target_type == AllocationTargetType.INVOICE:
                inv_res = await db.execute(
                    select(Invoice)
                    .where(Invoice.id == alloc_item.invoice_id, Invoice.organisation_id == org_id)
                    .with_for_update()
                )
                inv = inv_res.scalar_one_or_none()
                if not inv:
                    raise NotFoundError("Invoice not found in organisation.")

                if inv.status in (InvoiceStatus.DRAFT, InvoiceStatus.VOID):
                    raise ValidationFailedError(f"Cannot allocate to invoice in status '{inv.status.value}'.")

                if alloc_item.amount > inv.amount_due:
                    raise ValidationFailedError(
                        f"Allocation amount ({alloc_item.amount}) exceeds invoice balance due ({inv.amount_due})."
                    )

                inv.amount_paid += alloc_item.amount
                inv.amount_due = inv.total - inv.amount_paid
                if inv.amount_due == Decimal("0.0000"):
                    inv.status = InvoiceStatus.PAID
                else:
                    inv.status = InvoiceStatus.PARTIALLY_PAID

            elif alloc_item.target_type == AllocationTargetType.BILL:
                bill_res = await db.execute(
                    select(Bill)
                    .where(Bill.id == alloc_item.bill_id, Bill.organisation_id == org_id)
                    .with_for_update()
                )
                bill = bill_res.scalar_one_or_none()
                if not bill:
                    raise NotFoundError("Supplier bill not found in organisation.")

                if bill.status in (BillStatus.DRAFT, BillStatus.AWAITING_APPROVAL, BillStatus.REJECTED, BillStatus.VOID):
                    raise ValidationFailedError(f"Cannot allocate to bill in status '{bill.status.value}'.")

                if alloc_item.amount > bill.amount_due:
                    raise ValidationFailedError(
                        f"Allocation amount ({alloc_item.amount}) exceeds bill balance due ({bill.amount_due})."
                    )

                bill.amount_paid += alloc_item.amount
                bill.amount_due = bill.total - bill.amount_paid
                if bill.amount_due == Decimal("0.0000"):
                    bill.status = BillStatus.PAID
                else:
                    bill.status = BillStatus.PARTIALLY_PAID

            alloc_rec = PaymentAllocation(
                organisation_id=org_id,
                payment_id=payment.id,
                target_type=alloc_item.target_type,
                invoice_id=alloc_item.invoice_id,
                bill_id=alloc_item.bill_id,
                amount=alloc_item.amount,
                allocated_at=datetime.now(UTC),
                allocated_by_id=user_id,
                notes=alloc_item.notes,
            )
            db.add(alloc_rec)

        payment.allocated_amount += add_alloc_total
        payment.unallocated_amount -= add_alloc_total

        await AuditService.log_static(
            db=db,
            action="PAYMENT_ALLOCATED",
            resource_type="payment",
            resource_id=str(payment.id),
            organisation_id=org_id,
            user_id=user_id,
            diff={"additional_allocated": str(add_alloc_total), "remaining_unallocated": str(payment.unallocated_amount)},
        )
        await db.flush()

        return await PaymentService.get_payment(db, org_id, payment_id)

    @staticmethod
    async def void_payment(
        db: AsyncSession,
        org_id: uuid.UUID,
        payment_id: uuid.UUID,
        reason: str,
        user_id: uuid.UUID,
    ) -> PaymentDetailResponse:
        # Load payment with row lock
        p_res = await db.execute(
            select(Payment)
            .where(Payment.id == payment_id, Payment.organisation_id == org_id)
            .options(selectinload(Payment.allocations))
            .with_for_update()
        )
        payment = p_res.scalar_one_or_none()
        if not payment:
            raise NotFoundError("Payment not found in organisation.")

        if payment.status == PaymentStatus.VOIDED:
            raise ValidationFailedError("Payment is already voided.")

        # Reverse all allocations
        for alloc in payment.allocations:
            if alloc.target_type == AllocationTargetType.INVOICE and alloc.invoice_id:
                inv_res = await db.execute(
                    select(Invoice)
                    .where(Invoice.id == alloc.invoice_id, Invoice.organisation_id == org_id)
                    .with_for_update()
                )
                inv = inv_res.scalar_one_or_none()
                if inv:
                    inv.amount_paid -= alloc.amount
                    inv.amount_due = inv.total - inv.amount_paid
                    if inv.amount_paid == Decimal("0.0000"):
                        inv.status = InvoiceStatus.AWAITING_PAYMENT
                    else:
                        inv.status = InvoiceStatus.PARTIALLY_PAID

            elif alloc.target_type == AllocationTargetType.BILL and alloc.bill_id:
                bill_res = await db.execute(
                    select(Bill)
                    .where(Bill.id == alloc.bill_id, Bill.organisation_id == org_id)
                    .with_for_update()
                )
                bill = bill_res.scalar_one_or_none()
                if bill:
                    bill.amount_paid -= alloc.amount
                    bill.amount_due = bill.total - bill.amount_paid
                    if bill.amount_paid == Decimal("0.0000"):
                        bill.status = BillStatus.AWAITING_PAYMENT
                    else:
                        bill.status = BillStatus.PARTIALLY_PAID

        # Reverse bank account balance if connected
        if payment.bank_account_id:
            ba_res = await db.execute(
                select(BankAccount).where(
                    BankAccount.id == payment.bank_account_id,
                    BankAccount.organisation_id == org_id,
                )
            )
            bank_account = ba_res.scalar_one_or_none()
            if bank_account:
                if payment.payment_type == PaymentType.INCOMING:
                    bank_account.current_balance -= payment.amount
                elif payment.payment_type == PaymentType.OUTGOING:
                    bank_account.current_balance += payment.amount

        now = datetime.now(UTC)
        payment.status = PaymentStatus.VOIDED
        payment.voided_at = now
        payment.voided_by_id = user_id
        payment.void_reason = reason
        payment.unallocated_amount = Decimal("0.0000")

        await AuditService.log_static(
            db=db,
            action="PAYMENT_VOIDED",
            resource_type="payment",
            resource_id=str(payment.id),
            organisation_id=org_id,
            user_id=user_id,
            diff={"reason": reason, "reversed_amount": str(payment.amount)},
        )
        await db.flush()

        return await PaymentService.get_payment(db, org_id, payment_id)

    @staticmethod
    async def get_payment(
        db: AsyncSession,
        org_id: uuid.UUID,
        payment_id: uuid.UUID,
    ) -> PaymentDetailResponse:
        stmt = (
            select(Payment)
            .where(Payment.id == payment_id, Payment.organisation_id == org_id)
            .options(
                selectinload(Payment.allocations),
                selectinload(Payment.contact),
                selectinload(Payment.bank_account),
            )
        )
        result = await db.execute(stmt)
        payment = result.scalar_one_or_none()
        if not payment:
            raise NotFoundError("Payment not found in organisation.")

        alloc_responses = []
        for a in payment.allocations:
            target_num = None
            if a.target_type == AllocationTargetType.INVOICE and a.invoice_id:
                inv = await db.get(Invoice, a.invoice_id)
                if inv:
                    target_num = inv.invoice_number
            elif a.target_type == AllocationTargetType.BILL and a.bill_id:
                bill = await db.get(Bill, a.bill_id)
                if bill:
                    target_num = bill.internal_bill_number

            alloc_responses.append(
                PaymentAllocationResponse(
                    id=a.id,
                    organisation_id=org_id,
                    payment_id=payment.id,
                    target_type=a.target_type,
                    invoice_id=a.invoice_id,
                    bill_id=a.bill_id,
                    target_number=target_num,
                    amount=a.amount,
                    allocated_at=a.allocated_at,
                    allocated_by_id=a.allocated_by_id,
                    notes=a.notes,
                )
            )

        return PaymentDetailResponse(
            id=payment.id,
            organisation_id=payment.organisation_id,
            payment_number=payment.payment_number,
            payment_type=payment.payment_type,
            status=payment.status,
            contact_id=payment.contact_id,
            contact_name=payment.contact.business_name if payment.contact else None,
            bank_account_id=payment.bank_account_id,
            bank_account_name=payment.bank_account.account_name if payment.bank_account else None,
            payment_date=payment.payment_date,
            amount=payment.amount,
            currency=payment.currency,
            payment_method=payment.payment_method,
            reference=payment.reference,
            allocated_amount=payment.allocated_amount,
            unallocated_amount=payment.unallocated_amount,
            notes=payment.notes,
            created_by_id=payment.created_by_id,
            voided_by_id=payment.voided_by_id,
            voided_at=payment.voided_at,
            void_reason=payment.void_reason,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
            allocations=alloc_responses,
        )

    @staticmethod
    async def list_payments(
        db: AsyncSession,
        org_id: uuid.UUID,
        payment_type: Optional[PaymentType] = None,
        status: Optional[PaymentStatus] = None,
        contact_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[PaymentResponse], int]:
        stmt = (
            select(Payment)
            .where(Payment.organisation_id == org_id)
            .options(
                selectinload(Payment.contact),
                selectinload(Payment.bank_account),
            )
        )
        if payment_type:
            stmt = stmt.where(Payment.payment_type == payment_type)
        if status:
            stmt = stmt.where(Payment.status == status)
        if contact_id:
            stmt = stmt.where(Payment.contact_id == contact_id)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        # Paginate
        stmt = stmt.order_by(Payment.payment_date.desc(), Payment.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()

        responses = [
            PaymentResponse(
                id=p.id,
                organisation_id=p.organisation_id,
                payment_number=p.payment_number,
                payment_type=p.payment_type,
                status=p.status,
                contact_id=p.contact_id,
                contact_name=p.contact.business_name if p.contact else None,
                bank_account_id=p.bank_account_id,
                bank_account_name=p.bank_account.account_name if p.bank_account else None,
                payment_date=p.payment_date,
                amount=p.amount,
                currency=p.currency,
                payment_method=p.payment_method,
                reference=p.reference,
                allocated_amount=p.allocated_amount,
                unallocated_amount=p.unallocated_amount,
                notes=p.notes,
                created_by_id=p.created_by_id,
                voided_by_id=p.voided_by_id,
                voided_at=p.voided_at,
                void_reason=p.void_reason,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in items
        ]
        return responses, total

    @staticmethod
    async def get_metrics(
        db: AsyncSession,
        org_id: uuid.UUID,
    ) -> PaymentMetricsResponse:
        # Sum incoming posted
        inc_res = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), Decimal("0.0000"))).where(
                Payment.organisation_id == org_id,
                Payment.payment_type == PaymentType.INCOMING,
                Payment.status == PaymentStatus.POSTED,
            )
        )
        total_in = inc_res.scalar_one()

        # Sum outgoing posted
        out_res = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), Decimal("0.0000"))).where(
                Payment.organisation_id == org_id,
                Payment.payment_type == PaymentType.OUTGOING,
                Payment.status == PaymentStatus.POSTED,
            )
        )
        total_out = out_res.scalar_one()

        # Sum unallocated funds
        unalloc_res = await db.execute(
            select(func.coalesce(func.sum(Payment.unallocated_amount), Decimal("0.0000"))).where(
                Payment.organisation_id == org_id,
                Payment.status == PaymentStatus.POSTED,
            )
        )
        total_unalloc = unalloc_res.scalar_one()

        # Count total
        count_res = await db.execute(
            select(func.count(Payment.id)).where(Payment.organisation_id == org_id)
        )
        total_count = count_res.scalar_one()

        return PaymentMetricsResponse(
            total_incoming=total_in,
            total_outgoing=total_out,
            total_unallocated=total_unalloc,
            total_payments_count=total_count,
            currency="GBP",
        )
