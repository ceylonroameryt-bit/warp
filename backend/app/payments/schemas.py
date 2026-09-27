"""
Warp Ladger — Payments & Allocations Schemas (Phase 6)
Pydantic v2 schemas for bank accounts, payments, and multi-document allocations.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.database.models import (
    AllocationTargetType,
    BankAccountType,
    PaymentMethod,
    PaymentStatus,
    PaymentType,
)


# ─── Bank Account Schemas ─────────────────────────────────────
class BankAccountCreate(BaseModel):
    account_name: str = Field(..., min_length=1, max_length=100)
    account_type: BankAccountType = BankAccountType.CHECKING
    currency: str = Field("GBP", min_length=3, max_length=3)
    account_number: Optional[str] = Field(None, max_length=50)
    sort_code: Optional[str] = Field(None, max_length=20)
    iban: Optional[str] = Field(None, max_length=50)
    bic_swift: Optional[str] = Field(None, max_length=20)
    opening_balance: Decimal = Field(Decimal("0.0000"))
    is_default: bool = False


class BankAccountUpdate(BaseModel):
    account_name: Optional[str] = Field(None, min_length=1, max_length=100)
    account_type: Optional[BankAccountType] = None
    account_number: Optional[str] = None
    sort_code: Optional[str] = None
    iban: Optional[str] = None
    bic_swift: Optional[str] = None
    is_default: Optional[bool] = None
    active: Optional[bool] = None


class BankAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    account_name: str
    account_type: BankAccountType
    currency: str
    account_number: Optional[str] = None
    sort_code: Optional[str] = None
    iban: Optional[str] = None
    bic_swift: Optional[str] = None
    opening_balance: Decimal
    current_balance: Decimal
    is_default: bool
    active: bool
    created_at: datetime
    updated_at: datetime


# ─── Allocation Schemas ───────────────────────────────────────
class PaymentAllocationCreate(BaseModel):
    target_type: AllocationTargetType
    invoice_id: Optional[uuid.UUID] = None
    bill_id: Optional[uuid.UUID] = None
    amount: Decimal = Field(..., gt=Decimal("0.0000"))
    notes: Optional[str] = None


class PaymentAllocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    payment_id: uuid.UUID
    target_type: AllocationTargetType
    invoice_id: Optional[uuid.UUID] = None
    bill_id: Optional[uuid.UUID] = None
    target_number: Optional[str] = None  # e.g. INV-000001 or BILL-000001
    amount: Decimal
    allocated_at: datetime
    allocated_by_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


# ─── Payment Schemas ──────────────────────────────────────────
class PaymentCreate(BaseModel):
    payment_type: PaymentType
    contact_id: Optional[uuid.UUID] = None
    bank_account_id: Optional[uuid.UUID] = None
    payment_date: Optional[datetime] = None
    amount: Decimal = Field(..., gt=Decimal("0.0000"))
    currency: str = Field("GBP", min_length=3, max_length=3)
    payment_method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    reference: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    allocations: list[PaymentAllocationCreate] = Field(default_factory=list)


class PaymentAllocateRequest(BaseModel):
    allocations: list[PaymentAllocationCreate] = Field(..., min_length=1)


class PaymentVoidRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    payment_number: str
    payment_type: PaymentType
    status: PaymentStatus
    contact_id: Optional[uuid.UUID] = None
    contact_name: Optional[str] = None
    bank_account_id: Optional[uuid.UUID] = None
    bank_account_name: Optional[str] = None
    payment_date: datetime
    amount: Decimal
    currency: str
    payment_method: PaymentMethod
    reference: Optional[str] = None
    allocated_amount: Decimal
    unallocated_amount: Decimal
    notes: Optional[str] = None
    created_by_id: Optional[uuid.UUID] = None
    voided_by_id: Optional[uuid.UUID] = None
    voided_at: Optional[datetime] = None
    void_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PaymentDetailResponse(PaymentResponse):
    allocations: list[PaymentAllocationResponse] = Field(default_factory=list)


class PaymentListResponse(BaseModel):
    items: list[PaymentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaymentMetricsResponse(BaseModel):
    total_incoming: Decimal
    total_outgoing: Decimal
    total_unallocated: Decimal
    total_payments_count: int
    currency: str = "GBP"
