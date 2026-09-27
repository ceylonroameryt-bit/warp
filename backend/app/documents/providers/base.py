"""
Warp Ladger — Document Extraction Provider Interface (ABC)
Decoupled abstraction layer supporting Fake, Google Document AI, Azure, and Multimodal LLMs.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from app.database.models import DocumentType


@dataclass
class ClassificationOutput:
    document_type: DocumentType
    confidence: Decimal
    raw_text_sample: Optional[str] = None


@dataclass
class FieldExtraction:
    name: str
    raw_value: Optional[str] = None
    normalized_value: Optional[str] = None
    confidence: Decimal = Decimal("0.95")
    page: Optional[int] = 1
    bounding_box: Optional[dict[str, Any]] = None
    source_text: Optional[str] = None


@dataclass
class LineExtraction:
    position: int
    description: str
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    net_amount: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    gross_amount: Optional[Decimal] = None
    confidence: Decimal = Decimal("0.95")
    page: Optional[int] = 1


@dataclass
class ExtractionOutput:
    provider_name: str
    provider_model: str
    document_type: DocumentType
    document_type_confidence: Decimal

    # Supplier info
    supplier_name: Optional[str] = None
    supplier_address: Optional[str] = None
    supplier_email: Optional[str] = None
    supplier_phone: Optional[str] = None
    supplier_vat_number: Optional[str] = None
    supplier_company_number: Optional[str] = None

    # Invoice info
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    purchase_order_number: Optional[str] = None
    reference: Optional[str] = None
    currency: Optional[str] = "GBP"

    # Financials
    subtotal: Optional[Decimal] = None
    discount_total: Optional[Decimal] = Decimal("0")
    tax_total: Optional[Decimal] = None
    total: Optional[Decimal] = None

    # Detailed items
    fields: list[FieldExtraction] = field(default_factory=list)
    lines: list[LineExtraction] = field(default_factory=list)

    # Security & Provenance
    has_bank_details: bool = False
    detected_bank_details: Optional[dict[str, str]] = None
    page_count: int = 1
    raw_result: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 250
    estimated_cost_usd: Decimal = Decimal("0.005")


class DocumentExtractionProvider(ABC):
    """Abstract interface for all document OCR / extraction backends."""

    @abstractmethod
    async def classify_document(
        self, data: bytes, content_type: str, filename: str
    ) -> ClassificationOutput:
        """Identify document category (SUPPLIER_INVOICE, RECEIPT, etc.)."""
        pass

    @abstractmethod
    async def extract_document(
        self, data: bytes, content_type: str, filename: str
    ) -> ExtractionOutput:
        """Extract structured fields, financial calculations, line items, and provenance."""
        pass

    @abstractmethod
    def get_metadata(self) -> dict[str, Any]:
        """Provider identification and capabilities."""
        pass
