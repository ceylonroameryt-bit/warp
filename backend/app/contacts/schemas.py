"""
Warp Ladger — Contacts Pydantic Schemas
Comprehensive schemas for contacts, contact persons, addresses, notes, documents,
duplicate detection, and CSV import/export.
"""
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.database.models import AddressType, ContactStatus, ContactType


# ─── Contact People ──────────────────────────────────────────
class ContactPersonBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    job_title: Optional[str] = Field(default=None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=50)
    mobile: Optional[str] = Field(default=None, max_length=50)
    department: Optional[str] = Field(default=None, max_length=100)
    is_primary: bool = Field(default=False)
    status: str = Field(default="active", max_length=20)


class ContactPersonCreate(ContactPersonBase):
    pass


class ContactPersonUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    job_title: Optional[str] = Field(default=None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=50)
    mobile: Optional[str] = Field(default=None, max_length=50)
    department: Optional[str] = Field(default=None, max_length=100)
    is_primary: Optional[bool] = None
    status: Optional[str] = Field(default=None, max_length=20)


class ContactPersonResponse(ContactPersonBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contact_id: uuid.UUID
    organisation_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ─── Contact Addresses ───────────────────────────────────────
class ContactAddressBase(BaseModel):
    address_type: AddressType = Field(default=AddressType.BILLING)
    line1: str = Field(..., min_length=1, max_length=255)
    line2: Optional[str] = Field(default=None, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    county_region: Optional[str] = Field(default=None, max_length=100)
    postcode: Optional[str] = Field(default=None, max_length=20)
    country_code: str = Field(default="GB", min_length=2, max_length=2)
    is_primary: bool = Field(default=False)

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        code = v.strip().upper()
        if len(code) != 2 or not code.isalpha():
            raise ValueError("Country code must be a valid 2-letter ISO 3166-1 alpha-2 code")
        return code


class ContactAddressCreate(ContactAddressBase):
    pass


class ContactAddressUpdate(BaseModel):
    address_type: Optional[AddressType] = None
    line1: Optional[str] = Field(default=None, min_length=1, max_length=255)
    line2: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, min_length=1, max_length=100)
    county_region: Optional[str] = Field(default=None, max_length=100)
    postcode: Optional[str] = Field(default=None, max_length=20)
    country_code: Optional[str] = Field(default=None, min_length=2, max_length=2)
    is_primary: Optional[bool] = None

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            code = v.strip().upper()
            if len(code) != 2 or not code.isalpha():
                raise ValueError("Country code must be a valid 2-letter ISO 3166-1 alpha-2 code")
            return code
        return v


class ContactAddressResponse(ContactAddressBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contact_id: uuid.UUID
    organisation_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ─── Contact Notes ───────────────────────────────────────────
class ContactNoteCreate(BaseModel):
    content: str = Field(..., min_length=1, description="Internal note content")


class ContactNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contact_id: uuid.UUID
    organisation_id: uuid.UUID
    content: str
    created_by_id: Optional[uuid.UUID] = None
    created_by_name: Optional[str] = None
    created_at: datetime


# ─── Contact Documents (FileLink) ────────────────────────────
class ContactDocumentAttach(BaseModel):
    file_id: uuid.UUID


class ContactDocumentResponse(BaseModel):
    id: uuid.UUID
    file_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
    created_by_id: Optional[uuid.UUID] = None


# ─── Contact Core Schemas ────────────────────────────────────
class ContactBase(BaseModel):
    contact_type: ContactType = Field(default=ContactType.CUSTOMER)
    business_name: str = Field(..., min_length=1, max_length=255)
    legal_name: Optional[str] = Field(default=None, max_length=255)
    display_name: Optional[str] = Field(default=None, max_length=255)
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=50)
    mobile: Optional[str] = Field(default=None, max_length=50)
    website: Optional[str] = Field(default=None, max_length=255)
    company_number: Optional[str] = Field(default=None, max_length=50)
    vat_number: Optional[str] = Field(default=None, max_length=50)
    tax_identifier: Optional[str] = Field(default=None, max_length=50)
    currency: str = Field(default="GBP", min_length=3, max_length=3)
    payment_terms_id: Optional[uuid.UUID] = None
    reference: Optional[str] = Field(default=None, max_length=50)
    credit_limit: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = None
    status: ContactStatus = Field(default=ContactStatus.ACTIVE)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        curr = v.strip().upper()
        if len(curr) != 3 or not curr.isalpha():
            raise ValueError("Currency must be a 3-letter ISO 4217 code")
        return curr

    @field_validator("business_name")
    @classmethod
    def validate_business_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Business name cannot be empty")
        return cleaned


class ContactCreate(ContactBase):
    primary_contact: Optional[ContactPersonCreate] = None
    billing_address: Optional[ContactAddressCreate] = None
    shipping_address: Optional[ContactAddressCreate] = None


class ContactQuickCreate(BaseModel):
    contact_type: ContactType = Field(default=ContactType.CUSTOMER)
    business_name: str = Field(..., min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=50)
    currency: str = Field(default="GBP", min_length=3, max_length=3)


class ContactUpdate(BaseModel):
    contact_type: Optional[ContactType] = None
    business_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    legal_name: Optional[str] = Field(default=None, max_length=255)
    display_name: Optional[str] = Field(default=None, max_length=255)
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=50)
    mobile: Optional[str] = Field(default=None, max_length=50)
    website: Optional[str] = Field(default=None, max_length=255)
    company_number: Optional[str] = Field(default=None, max_length=50)
    vat_number: Optional[str] = Field(default=None, max_length=50)
    tax_identifier: Optional[str] = Field(default=None, max_length=50)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    payment_terms_id: Optional[uuid.UUID] = None
    reference: Optional[str] = Field(default=None, max_length=50)
    credit_limit: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = None
    status: Optional[ContactStatus] = None


class ContactResponse(ContactBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    primary_contact_phone: Optional[str] = None
    payment_terms_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None


class ContactDetailResponse(ContactResponse):
    people: list[ContactPersonResponse] = []
    addresses: list[ContactAddressResponse] = []
    internal_notes: list[ContactNoteResponse] = []
    documents: list[ContactDocumentResponse] = []
    tags: list[str] = []


class ContactListResponse(BaseModel):
    items: list[ContactResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ─── Duplicate Detection ─────────────────────────────────────
class DuplicateCheckRequest(BaseModel):
    business_name: str = Field(..., min_length=1)
    email: Optional[str] = None
    vat_number: Optional[str] = None
    company_number: Optional[str] = None
    exclude_contact_id: Optional[uuid.UUID] = None


class DuplicateMatch(BaseModel):
    contact_id: uuid.UUID
    business_name: str
    matched_fields: list[str]
    confidence: str  # "HIGH", "MEDIUM"
    message: str


class DuplicateCheckResponse(BaseModel):
    has_duplicates: bool
    matches: list[DuplicateMatch]


# ─── CSV Import & Export ─────────────────────────────────────
class ContactImportRowValidation(BaseModel):
    row_number: int
    valid: bool
    errors: list[str] = []
    warnings: list[str] = []
    data: dict[str, Any] = {}


class ContactImportPreviewResult(BaseModel):
    total_rows: int
    valid_rows: int
    warning_count: int
    error_count: int
    rows: list[ContactImportRowValidation]


class ContactImportExecuteRequest(BaseModel):
    rows: list[dict[str, Any]]
    skip_errors: bool = True


class ContactImportExecuteResult(BaseModel):
    created_count: int
    skipped_count: int
    errors: list[dict[str, Any]] = []
