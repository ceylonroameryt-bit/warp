"""
Warp Ladger — Payments & Bank Accounts API Router (Phase 6)
All endpoints enforce multi-tenancy and 8-role RBAC permissions.
"""
from datetime import datetime
from decimal import Decimal
import math
from typing import Optional
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.dependencies import (
    CurrentUser,
    DBSession,
    OrgMembership,
    require_permission,
)
from app.database.models import (
    PaymentMethod,
    PaymentStatus,
    PaymentType,
)
from app.payments.schemas import (
    BankAccountCreate,
    BankAccountResponse,
    BankAccountUpdate,
    PaymentAllocateRequest,
    PaymentCreate,
    PaymentDetailResponse,
    PaymentListResponse,
    PaymentMetricsResponse,
    PaymentResponse,
    PaymentVoidRequest,
)
from app.payments.service import PaymentService

log = structlog.get_logger(__name__)

payments_router = APIRouter()
bank_accounts_router = APIRouter()


# ═══════════════════════════════════════════════════════════════════
# PAYMENTS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@payments_router.get(
    "/metrics",
    response_model=PaymentMetricsResponse,
    dependencies=[Depends(require_permission("payments", "read"))],
)
async def get_payment_metrics(
    org_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
):
    """Retrieve financial summary metrics for incoming and outgoing payments."""
    return await PaymentService.get_metrics(db, org_id)


@payments_router.get(
    "",
    response_model=PaymentListResponse,
    dependencies=[Depends(require_permission("payments", "read"))],
)
async def list_payments(
    org_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
    payment_type: Optional[PaymentType] = Query(None),
    status: Optional[PaymentStatus] = Query(None),
    contact_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """List all payments scoped to this organisation with filtering and pagination."""
    items, total = await PaymentService.list_payments(
        db=db,
        org_id=org_id,
        payment_type=payment_type,
        status=status,
        contact_id=contact_id,
        page=page,
        page_size=page_size,
    )
    total_pages = max(1, math.ceil(total / page_size))
    return PaymentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@payments_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=PaymentDetailResponse,
    dependencies=[Depends(require_permission("payments", "create"))],
)
async def record_payment(
    org_id: uuid.UUID,
    payload: PaymentCreate,
    current_user: CurrentUser,
    db: DBSession,
    membership: OrgMembership,
):
    """
    Record an incoming or outgoing payment.
    Atomically generates sequential payment numbers and processes optional multi-item allocations.
    """
    resp = await PaymentService.record_payment(
        db=db,
        org_id=org_id,
        payload=payload,
        user_id=current_user.id,
    )
    await db.commit()
    return resp


@payments_router.get(
    "/{payment_id}",
    response_model=PaymentDetailResponse,
    dependencies=[Depends(require_permission("payments", "read"))],
)
async def get_payment(
    org_id: uuid.UUID,
    payment_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
):
    """Retrieve full details of a payment including all line allocations."""
    return await PaymentService.get_payment(db, org_id, payment_id)


@payments_router.post(
    "/{payment_id}/allocate",
    response_model=PaymentDetailResponse,
    dependencies=[Depends(require_permission("payments", "create"))],
)
async def allocate_payment(
    org_id: uuid.UUID,
    payment_id: uuid.UUID,
    payload: PaymentAllocateRequest,
    current_user: CurrentUser,
    db: DBSession,
    membership: OrgMembership,
):
    """Allocate unallocated funds on an existing payment to open invoices or bills."""
    resp = await PaymentService.allocate_payment(
        db=db,
        org_id=org_id,
        payment_id=payment_id,
        payload=payload,
        user_id=current_user.id,
    )
    await db.commit()
    return resp


@payments_router.post(
    "/{payment_id}/void",
    response_model=PaymentDetailResponse,
    dependencies=[Depends(require_permission("payments", "void"))],
)
async def void_payment(
    org_id: uuid.UUID,
    payment_id: uuid.UUID,
    payload: PaymentVoidRequest,
    current_user: CurrentUser,
    db: DBSession,
    membership: OrgMembership,
):
    """
    Void a posted payment.
    Atomically reverses all linked allocations, restores invoice/bill balances, and audits reason.
    """
    resp = await PaymentService.void_payment(
        db=db,
        org_id=org_id,
        payment_id=payment_id,
        reason=payload.reason,
        user_id=current_user.id,
    )
    await db.commit()
    return resp


# ═══════════════════════════════════════════════════════════════════
# BANK ACCOUNTS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@bank_accounts_router.get(
    "",
    response_model=list[BankAccountResponse],
    dependencies=[Depends(require_permission("bank_accounts", "read"))],
)
async def list_bank_accounts(
    org_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
):
    """List active bank accounts for this organisation."""
    return await PaymentService.list_bank_accounts(db, org_id)


@bank_accounts_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=BankAccountResponse,
    dependencies=[Depends(require_permission("bank_accounts", "manage"))],
)
async def create_bank_account(
    org_id: uuid.UUID,
    payload: BankAccountCreate,
    current_user: CurrentUser,
    db: DBSession,
    membership: OrgMembership,
):
    """Create a new company bank account."""
    resp = await PaymentService.create_bank_account(
        db=db,
        org_id=org_id,
        payload=payload,
        user_id=current_user.id,
    )
    await db.commit()
    return resp


@bank_accounts_router.get(
    "/{account_id}",
    response_model=BankAccountResponse,
    dependencies=[Depends(require_permission("bank_accounts", "read"))],
)
async def get_bank_account(
    org_id: uuid.UUID,
    account_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
):
    """Get bank account details."""
    return await PaymentService.get_bank_account(db, org_id, account_id)
