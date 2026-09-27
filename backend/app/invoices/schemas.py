"""
Warp Ladger — Invoice Pydantic Schemas
All monetary fields use Decimal, never float.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.database.models import DeliveryStatus, DiscountType, InvoiceStatus, TaxType


# ─── Tax Rate Schemas ─────────────────────────────────────────
class TaxRateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20)
    rate: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"), decimal_places=4)
    tax_type: TaxType = TaxType.STANDARD
    active: bool = True
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None

    @field_validator("code")
    @classmethod
    def code_upper(cls, v: str) -> str:
        return v.strip().upper()


class TaxRateCreate(TaxRateBase):
    pass


class TaxRateUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    code: Optional[str] = Field(default=None, min_length=1, max_length=20)
    rate: Optional[Decimal] = Field(default=None, ge=Decimal("0"), le=Decimal("100"))
    tax_type: Optional[TaxType] = None
    active: Optional[bool] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None


class TaxRateResponse(TaxRateBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    organisation_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ─── Invoice Line Schemas ─────────────────────────────────────
class InvoiceLineCreate(BaseModel):
    description: str = Field(..., min_length=1)
    quantity: Decimal = Field(..., gt=Decimal("0"), decimal_places=4)
    unit_price: Decimal = Field(..., ge=Decimal("0"), decimal_places=4)
    tax_rate_id: Optional[uuid.UUID] = None
    discount_type: Optional[DiscountType] = None
    discount_value: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), decimal_places=4)
    position: int = Field(default=0, ge=0)


class InvoiceLineUpdate(BaseModel):
    description: Optional[str] = Field(default=None, min_length=1)
    quantity: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    unit_price: Optional[Decimal] = Field(default=None, ge=Decimal("0"))
    tax_rate_id: Optional[uuid.UUID] = None
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[Decimal] = Field(default=None, ge=Decimal("0"))
    position: Optional[int] = Field(default=None, ge=0)


class InvoiceLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    invoice_id: uuid.UUID
    organisation_id: uuid.UUID
    position: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount_type: Optional[DiscountType] = None
    discount_value: Decimal
    net_amount: Decimal
    tax_rate_id: Optional[uuid.UUID] = None
    tax_rate_snapshot: Optional[Decimal] = None
    tax_amount: Decimal
    gross_amount: Decimal
    created_at: datetime
    updated_at: datetime


# ─── Invoice Core Schemas ─────────────────────────────────────
class InvoiceCreate(BaseModel):
    customer_id: uuid.UUID
    issue_date: datetime
    due_date: datetime
    currency: str = Field(default="GBP", min_length=3, max_length=3)
    payment_terms_id: Optional[uuid.UUID] = None
    customer_reference: Optional[str] = Field(default=None, max_length=100)
    purchase_order_reference: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = None
    terms: Optional[str] = None
    internal_notes: Optional[str] = None
    lines: list[InvoiceLineCreate] = Field(..., min_length=1)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("due_date")
    @classmethod
    def due_after_issue(cls, v: datetime, info) -> datetime:
        issue = info.data.get("issue_date")
        if issue and v < issue:
            raise ValueError("Due date cannot be before issue date.")
        return v


class InvoiceUpdate(BaseModel):
    """Allowed for DRAFT invoices only."""
    customer_id: Optional[uuid.UUID] = None
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    payment_terms_id: Optional[uuid.UUID] = None
    customer_reference: Optional[str] = Field(default=None, max_length=100)
    purchase_order_reference: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = None
    terms: Optional[str] = None
    internal_notes: Optional[str] = None
    lines: Optional[list[InvoiceLineCreate]] = None


class InvoiceApproveRequest(BaseModel):
    idempotency_key: Optional[str] = Field(default=None, max_length=64)


class InvoiceVoidRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class InvoiceSendRequest(BaseModel):
    recipient_email: EmailStr
    cc: Optional[str] = Field(default=None, max_length=500)
    subject: Optional[str] = Field(default=None, max_length=255)
    message: Optional[str] = None
    attach_pdf: bool = True


# ─── Invoice Response Schemas ─────────────────────────────────
class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    customer_id: Optional[uuid.UUID] = None
    invoice_number: Optional[str] = None
    status: InvoiceStatus
    # Derived OVERDUE is computed in service layer
    effective_status: str = "DRAFT"  # includes computed OVERDUE
    issue_date: datetime
    due_date: datetime
    currency: str
    customer_reference: Optional[str] = None
    purchase_order_reference: Optional[str] = None
    payment_terms_id: Optional[uuid.UUID] = None
    # Snapshot fields
    customer_name_snapshot: Optional[str] = None
    customer_email_snapshot: Optional[str] = None
    customer_vat_number_snapshot: Optional[str] = None
    billing_address_snapshot: Optional[dict] = None
    # Financials
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    # Notes
    notes: Optional[str] = None
    terms: Optional[str] = None
    # Workflow
    approved_by_id: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    voided_at: Optional[datetime] = None
    void_reason: Optional[str] = None
    created_by_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class InvoiceDetailResponse(InvoiceResponse):
    """Full detail including lines, deliveries, and internal notes."""
    internal_notes: Optional[str] = None
    lines: list[InvoiceLineResponse] = []
    deliveries: list["InvoiceDeliveryResponse"] = []


class InvoiceListResponse(BaseModel):
    items: list[InvoiceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ─── Invoice Delivery Response ────────────────────────────────
class InvoiceDeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_id: uuid.UUID
    recipient_email: str
    cc: Optional[str] = None
    subject: str
    status: DeliveryStatus
    sent_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    retry_count: int
    created_at: datetime


# ─── Invoice Filters ──────────────────────────────────────────
class InvoiceFilters(BaseModel):
    status: Optional[str] = None          # supports "OVERDUE" as derived
    customer_id: Optional[uuid.UUID] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    currency: Optional[str] = None
    search: Optional[str] = None          # invoice_number, customer_name_snapshot, ref
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
    sort_by: str = Field(default="created_at")
    sort_dir: str = Field(default="desc")
