"""
Warp Ladger — Smart Document Capture Schemas (Pydantic v2)
All monetary quantities use Decimal.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.database.models import DocumentProcessingStatus, DocumentType, ExtractionJobStatus


# ─── Helpers ─────────────────────────────────────────────────
def get_confidence_level(score: Optional[Decimal | float]) -> str:
    """Translate numeric confidence score into user-friendly category."""
    if score is None:
        return "LOW"
    val = float(score)
    if val >= 0.95:
        return "HIGH"
    if val >= 0.80:
        return "MEDIUM"
    return "LOW"


# ─── Field Extraction Models ─────────────────────────────────
class DocumentExtractionFieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    extraction_id: uuid.UUID
    field_name: str
    raw_value: Optional[str] = None
    normalized_value: Optional[str] = None
    confidence: Optional[Decimal] = None
    confidence_level: Optional[str] = None
    page_number: Optional[int] = None
    bounding_box: Optional[dict[str, Any]] = None
    source_text: Optional[str] = None
    manually_corrected: bool = False
    original_value: Optional[str] = None
    corrected_by_id: Optional[uuid.UUID] = None
    corrected_at: Optional[datetime] = None


class DocumentExtractionLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    extraction_id: uuid.UUID
    position: int
    description: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    net_amount: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    gross_amount: Optional[Decimal] = None
    confidence: Optional[Decimal] = None
    confidence_level: Optional[str] = None
    page_number: Optional[int] = None
    manually_corrected: bool = False


# ─── Sub-validation & Match Models ───────────────────────────
class SupplierMatchResponse(BaseModel):
    matched_supplier_id: Optional[uuid.UUID] = None
    supplier_name: Optional[str] = None
    vat_number: Optional[str] = None
    email: Optional[str] = None
    confidence: Optional[Decimal] = None
    match_reason: Optional[str] = None
    is_exact_match: bool = False


class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool = False
    severity: str = "NONE"  # NONE, WARN, BLOCK
    duplicate_document_id: Optional[uuid.UUID] = None
    duplicate_bill_id: Optional[uuid.UUID] = None
    duplicate_invoice_number: Optional[str] = None
    reason: Optional[str] = None


class MathValidationResponse(BaseModel):
    is_valid: bool = True
    subtotal: Optional[Decimal] = None
    discount_total: Optional[Decimal] = None
    tax_total: Optional[Decimal] = None
    calculated_total: Optional[Decimal] = None
    declared_total: Optional[Decimal] = None
    difference: Optional[Decimal] = None
    notes: Optional[str] = None
    has_bank_details: bool = False
    bank_details_warning: Optional[str] = None


# ─── Extraction Aggregate Response ───────────────────────────
class DocumentExtractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    document_id: uuid.UUID
    provider: str
    provider_model: Optional[str] = None
    schema_version: int = 1

    document_type: Optional[DocumentType] = None
    document_type_confidence: Optional[Decimal] = None
    classification_level: Optional[str] = None

    supplier_name_raw: Optional[str] = None
    supplier_name_normalized: Optional[str] = None
    supplier_address_raw: Optional[str] = None
    supplier_email: Optional[str] = None
    supplier_phone: Optional[str] = None
    supplier_vat_number: Optional[str] = None
    supplier_company_number: Optional[str] = None

    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    purchase_order_number: Optional[str] = None
    reference: Optional[str] = None
    currency: Optional[str] = "GBP"

    subtotal: Optional[Decimal] = None
    discount_total: Optional[Decimal] = None
    tax_total: Optional[Decimal] = None
    total: Optional[Decimal] = None

    math_valid: Optional[bool] = None
    math_validation_notes: Optional[str] = None
    tax_valid: Optional[bool] = None
    date_valid: Optional[bool] = None

    matched_supplier_id: Optional[uuid.UUID] = None
    matched_supplier_confidence: Optional[Decimal] = None
    supplier_match_reason: Optional[str] = None

    duplicate_document_id: Optional[uuid.UUID] = None
    duplicate_bill_id: Optional[uuid.UUID] = None
    duplicate_severity: Optional[str] = None

    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    is_current: bool = True
    created_at: datetime

    fields: list[DocumentExtractionFieldResponse] = Field(default_factory=list)
    lines: list[DocumentExtractionLineResponse] = Field(default_factory=list)
    supplier_match: Optional[SupplierMatchResponse] = None
    math_validation: Optional[MathValidationResponse] = None
    duplicate_check: Optional[DuplicateCheckResponse] = None


# ─── Captured Document Models ────────────────────────────────
class CapturedDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    file_id: uuid.UUID
    original_filename: str
    mime_type: str
    file_size_bytes: int
    checksum_sha256: str
    page_count: Optional[int] = None
    processing_status: DocumentProcessingStatus
    document_type: Optional[DocumentType] = None
    document_type_confidence: Optional[Decimal] = None
    current_extraction_id: Optional[uuid.UUID] = None
    created_bill_id: Optional[uuid.UUID] = None
    created_bill_number: Optional[str] = None
    created_by_id: Optional[uuid.UUID] = None
    user_document_type_override: Optional[DocumentType] = None
    file_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Summary extracted data when available
    supplier_name: Optional[str] = None
    invoice_number: Optional[str] = None
    total: Optional[Decimal] = None
    currency: Optional[str] = None

    # Full extraction details when requested
    extraction: Optional[DocumentExtractionResponse] = None
    extractions: list[DocumentExtractionResponse] = Field(default_factory=list)


class DocumentListResponse(BaseModel):
    items: list[CapturedDocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentInboxSummary(BaseModel):
    total_documents: int
    needs_review_count: int
    processing_count: int
    ready_count: int
    completed_count: int
    failed_count: int


# ─── Request Payloads ─────────────────────────────────────────
class FieldCorrectionRequest(BaseModel):
    field_name: str
    new_value: Optional[str] = None


class SingleFieldCorrectionRequest(BaseModel):
    corrected_value: Optional[str] = None
    new_value: Optional[str] = None

    @property
    def value(self) -> Optional[str]:
        return self.corrected_value or self.new_value


class BulkFieldCorrectionRequest(BaseModel):
    corrections: dict[str, Optional[str]]


class LineItemCorrectionRequest(BaseModel):
    position: int
    description: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None


class ClassificationOverrideRequest(BaseModel):
    document_type: DocumentType


class DuplicateOverrideRequest(BaseModel):
    reason: str = Field(..., min_length=3, description="Mandatory reason for duplicate override")


class CreateBillFromExtractionRequest(BaseModel):
    supplier_id: Optional[uuid.UUID] = None
    create_new_supplier: bool = False
    new_supplier_name: Optional[str] = None
    corrections: Optional[dict[str, Any]] = None
    duplicate_override_reason: Optional[str] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    expense_account_id: Optional[uuid.UUID] = None
    purchase_category: Optional[str] = "General Expense"
