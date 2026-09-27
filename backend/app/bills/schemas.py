"""
Warp Ladger — Supplier Bills Schemas (Pydantic v2)
All monetary fields use Python Decimal — never float.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.database.models import BillApprovalAction, BillDocumentType, BillStatus, DiscountType


# ─── Line Items ──────────────────────────────────────────────
class BillLineCreate(BaseModel):
    description: str = Field(..., min_length=1)
    quantity: Decimal = Field(..., gt=Decimal("0"))
    unit_price: Decimal = Field(..., ge=Decimal("0"))
    tax_rate_id: Optional[uuid.UUID] = None
    discount_type: Optional[DiscountType] = None
    discount_value: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    expense_account_id: Optional[uuid.UUID] = None
    purchase_category: Optional[str] = None
    position: Optional[int] = 0


class BillLineUpdate(BaseModel):
    id: Optional[uuid.UUID] = None
    description: str = Field(..., min_length=1)
    quantity: Decimal = Field(..., gt=Decimal("0"))
    unit_price: Decimal = Field(..., ge=Decimal("0"))
    tax_rate_id: Optional[uuid.UUID] = None
    discount_type: Optional[DiscountType] = None
    discount_value: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    expense_account_id: Optional[uuid.UUID] = None
    purchase_category: Optional[str] = None
    position: Optional[int] = 0


class BillLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    position: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount_type: Optional[DiscountType] = None
    discount_value: Decimal
    net_amount: Decimal
    tax_amount: Decimal
    gross_amount: Decimal
    tax_rate_id: Optional[uuid.UUID] = None
    tax_rate_snapshot: Optional[Decimal] = None
    expense_account_id: Optional[uuid.UUID] = None
    purchase_category: Optional[str] = None


# ─── Documents & Approval Events ─────────────────────────────
class BillDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bill_id: uuid.UUID
    file_id: uuid.UUID
    document_type: str
    checksum_sha256: Optional[str] = None
    filename: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    download_url: Optional[str] = None
    created_at: datetime


class BillApprovalEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_user_id: Optional[uuid.UUID] = None
    actor_name: Optional[str] = None
    action: BillApprovalAction
    comment: Optional[str] = None
    created_at: datetime


# ─── Bill CRUD ───────────────────────────────────────────────
class BillCreate(BaseModel):
    supplier_id: uuid.UUID
    supplier_invoice_number: str = Field(..., min_length=1, max_length=100)
    bill_date: datetime
    due_date: Optional[datetime] = None
    currency: Optional[str] = Field(default="GBP", max_length=3)
    supplier_reference: Optional[str] = Field(default=None, max_length=100)
    purchase_order_reference: Optional[str] = Field(default=None, max_length=100)
    payment_terms_id: Optional[uuid.UUID] = None
    purchase_category_id: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    lines: list[BillLineCreate] = Field(..., min_length=1)
    file_ids: Optional[list[uuid.UUID]] = Field(default_factory=list)
    duplicate_override_reason: Optional[str] = None
    source_document_id: Optional[uuid.UUID] = None
    source_extraction_id: Optional[uuid.UUID] = None


class BillUpdate(BaseModel):
    supplier_id: Optional[uuid.UUID] = None
    supplier_invoice_number: Optional[str] = Field(default=None, min_length=1, max_length=100)
    bill_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    currency: Optional[str] = Field(default=None, max_length=3)
    supplier_reference: Optional[str] = None
    purchase_order_reference: Optional[str] = None
    payment_terms_id: Optional[uuid.UUID] = None
    purchase_category_id: Optional[str] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    lines: Optional[list[BillLineUpdate]] = None
    version: Optional[int] = None
    duplicate_override_reason: Optional[str] = None


class BillSubmitRequest(BaseModel):
    comment: Optional[str] = None


class BillApproveRequest(BaseModel):
    comment: Optional[str] = None


class BillRejectRequest(BaseModel):
    reason: str = Field(..., min_length=3, description="Mandatory reason for rejection")


class BillVoidRequest(BaseModel):
    reason: str = Field(..., min_length=3, description="Mandatory reason for voiding")


class BillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    supplier_id: Optional[uuid.UUID] = None
    supplier_invoice_number: str
    supplier_invoice_number_normalized: str
    internal_bill_number: Optional[str] = None
    status: BillStatus
    effective_status: Optional[str] = None  # derived at runtime (e.g. OVERDUE)
    bill_date: datetime
    due_date: datetime
    currency: str
    supplier_reference: Optional[str] = None
    purchase_order_reference: Optional[str] = None
    supplier_name_snapshot: Optional[str] = None
    supplier_email_snapshot: Optional[str] = None
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    version: int
    created_at: datetime
    updated_at: datetime


class BillDetailResponse(BillResponse):
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    supplier_vat_number_snapshot: Optional[str] = None
    supplier_address_snapshot: Optional[Any] = None
    payment_terms_id: Optional[uuid.UUID] = None
    purchase_category_id: Optional[str] = None
    submitted_for_approval_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    voided_at: Optional[datetime] = None
    void_reason: Optional[str] = None
    duplicate_override_reason: Optional[str] = None
    source_document_id: Optional[uuid.UUID] = None
    source_extraction_id: Optional[uuid.UUID] = None
    lines: list[BillLineResponse] = Field(default_factory=list)
    documents: list[BillDocumentResponse] = Field(default_factory=list)
    approval_events: list[BillApprovalEventResponse] = Field(default_factory=list)


class BillListResponse(BaseModel):
    items: list[BillResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class BillFilters(BaseModel):
    status: Optional[str] = None
    supplier_id: Optional[uuid.UUID] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    due_date_from: Optional[str] = None
    due_date_to: Optional[str] = None
    currency: Optional[str] = None
    search: Optional[str] = None
    page: int = 1
    page_size: int = 25
    sort_by: str = "bill_date"
    sort_dir: str = "desc"


# ─── Duplicate Detection ─────────────────────────────────────
class DuplicateCheckRequest(BaseModel):
    supplier_id: uuid.UUID
    supplier_invoice_number: str
    bill_date: Optional[datetime] = None
    total: Optional[Decimal] = None
    file_checksum: Optional[str] = None
    exclude_bill_id: Optional[uuid.UUID] = None


class DuplicateMatch(BaseModel):
    bill_id: uuid.UUID
    internal_bill_number: Optional[str] = None
    supplier_invoice_number: str
    supplier_name: Optional[str] = None
    bill_date: datetime
    total: Decimal
    currency: str
    status: str
    match_type: str  # EXACT_INVOICE_NUMBER | EXACT_FILE_CHECKSUM | FUZZY_MATCH
    confidence_score: int
    reason: str


class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool
    severity: str  # NONE | WARNING | BLOCK
    matches: list[DuplicateMatch] = Field(default_factory=list)


# ─── Purchases Dashboard Metrics ─────────────────────────────
class PurchasesMetricsResponse(BaseModel):
    awaiting_approval_count: int
    awaiting_approval_amount: Decimal
    awaiting_payment_count: int
    awaiting_payment_amount: Decimal
    overdue_count: int
    overdue_amount: Decimal
    this_month_count: int
    this_month_amount: Decimal
