"""
Warp Ladger — All SQLAlchemy ORM Models
Single source of truth for all database tables.
"""
import uuid
from datetime import date, datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import (
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


# ─── Phase 3 Enums ───────────────────────────────────────────
class InvoiceStatus(str, PyEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    SENT = "SENT"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    VOID = "VOID"
    CREDITED = "CREDITED"


class DiscountType(str, PyEnum):
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"


class TaxType(str, PyEnum):
    STANDARD = "STANDARD"
    REDUCED = "REDUCED"
    ZERO = "ZERO"
    EXEMPT = "EXEMPT"
    OUTSIDE_SCOPE = "OUTSIDE_SCOPE"


class DeliveryStatus(str, PyEnum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    SENT = "SENT"
    FAILED_TEMPORARY = "FAILED_TEMPORARY"
    FAILED = "FAILED"


# ─── Phase 4 Enums ───────────────────────────────────────────
class BillStatus(str, PyEnum):
    DRAFT = "DRAFT"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    REJECTED = "REJECTED"
    VOID = "VOID"


class BillApprovalAction(str, PyEnum):
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RESUBMITTED = "RESUBMITTED"


class BillDocumentType(str, PyEnum):
    ORIGINAL_INVOICE = "ORIGINAL_INVOICE"
    SUPPORTING_DOCUMENT = "SUPPORTING_DOCUMENT"
    PURCHASE_ORDER = "PURCHASE_ORDER"
    OTHER = "OTHER"


# ─── Phase 5 Enums ───────────────────────────────────────────
class DocumentProcessingStatus(str, PyEnum):
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    EXTRACTING = "EXTRACTING"
    VALIDATING = "VALIDATING"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    DUPLICATE_FILE = "DUPLICATE_FILE"
    UNSUPPORTED = "UNSUPPORTED"
    NEEDS_MANUAL_REVIEW = "NEEDS_MANUAL_REVIEW"
    PROCESSED_RECEIPT = "PROCESSED_RECEIPT"
    CONVERTED_TO_BILL = "CONVERTED_TO_BILL"
    DISCARDED = "DISCARDED"


class DocumentType(str, PyEnum):
    SUPPLIER_INVOICE = "SUPPLIER_INVOICE"
    RECEIPT = "RECEIPT"
    CREDIT_NOTE = "CREDIT_NOTE"
    STATEMENT = "STATEMENT"
    PURCHASE_ORDER = "PURCHASE_ORDER"
    UNKNOWN = "UNKNOWN"


class ExtractionJobStatus(str, PyEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED_TEMPORARY = "FAILED_TEMPORARY"
    FAILED = "FAILED"
# ─── Phase 6 Enums: Payments & Bank Accounts ───────────────────
class PaymentType(str, PyEnum):
    INCOMING = "INCOMING"  # Customer Payment / Money In
    OUTGOING = "OUTGOING"  # Supplier Payment / Money Out


class PaymentStatus(str, PyEnum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    VOIDED = "VOIDED"
    REFUNDED = "REFUNDED"


class PaymentMethod(str, PyEnum):
    BANK_TRANSFER = "BANK_TRANSFER"
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    DIRECT_DEBIT = "DIRECT_DEBIT"
    CHECK = "CHECK"
    CASH = "CASH"
    OTHER = "OTHER"


class BankAccountType(str, PyEnum):
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"
    CREDIT_CARD = "CREDIT_CARD"


class AllocationTargetType(str, PyEnum):
    INVOICE = "INVOICE"
    BILL = "BILL"


# ─── Phase 7 Enums: Accounting Ledger ─────────────────────────
class AccountClass(str, PyEnum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"


class AccountSubtype(str, PyEnum):
    CURRENT_ASSET = "CURRENT_ASSET"
    FIXED_ASSET = "FIXED_ASSET"
    NON_CURRENT_ASSET = "NON_CURRENT_ASSET"
    CURRENT_LIABILITY = "CURRENT_LIABILITY"
    NON_CURRENT_LIABILITY = "NON_CURRENT_LIABILITY"
    EQUITY = "EQUITY"
    OPERATING_REVENUE = "OPERATING_REVENUE"
    OTHER_INCOME = "OTHER_INCOME"
    COST_OF_SALES = "COST_OF_SALES"
    EXPENSE = "EXPENSE"
    OVERHEAD = "OVERHEAD"


class JournalEntryStatus(str, PyEnum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    VOIDED = "VOIDED"
    REVERSED = "REVERSED"


class JournalSourceType(str, PyEnum):
    MANUAL = "MANUAL"
    INVOICE = "INVOICE"
    BILL = "BILL"
    PAYMENT = "PAYMENT"
    PAYROLL = "PAYROLL"
    REVERSAL = "REVERSAL"
    YEAR_END = "YEAR_END"
    OPENING_BALANCE = "OPENING_BALANCE"


# ─── Enums ───────────────────────────────────────────────────
class MembershipStatus(str, PyEnum):
    active = "active"
    invited = "invited"
    suspended = "suspended"


class InvitationStatus(str, PyEnum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"
    cancelled = "cancelled"


class OrganisationStatus(str, PyEnum):
    active = "active"
    suspended = "suspended"
    cancelled = "cancelled"


class AuthProviderType(str, PyEnum):
    local = "local"
    google = "google"
    github = "github"
    microsoft = "microsoft"


class ContactType(str, PyEnum):
    CUSTOMER = "CUSTOMER"
    SUPPLIER = "SUPPLIER"
    BOTH = "BOTH"


class ContactStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class AddressType(str, PyEnum):
    BILLING = "BILLING"
    SHIPPING = "SHIPPING"
    REGISTERED = "REGISTERED"
    OTHER = "OTHER"


class PaymentTermType(str, PyEnum):
    DAYS_AFTER_INVOICE = "DAYS_AFTER_INVOICE"
    DAYS_AFTER_MONTH_END = "DAYS_AFTER_MONTH_END"
    IMMEDIATE = "IMMEDIATE"


# ─── Plans (billing stub) ────────────────────────────────────
class Plan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Subscription plan stub. Billing wired in a later phase."""

    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    max_users: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_organisations: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    features: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    organisations: Mapped[list["Organisation"]] = relationship(back_populates="plan")


# ─── Users ───────────────────────────────────────────────────
class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Platform user account."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Email verification
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verification_token_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    email_verification_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # MFA (stub for Phase 1)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Password reset
    password_reset_token_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    password_reset_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Locale
    locale: Mapped[str] = mapped_column(String(10), default="en-GB", nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/London", nullable=False)

    # Relationships
    auth_providers: Mapped[list["AuthProvider"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
    invitations_sent: Mapped[list["Invitation"]] = relationship(
        back_populates="inviter", foreign_keys="Invitation.inviter_id"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


class AuthProvider(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """OAuth / local auth provider link for a user."""

    __tablename__ = "auth_providers"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_auth_provider_user_provider"),
        UniqueConstraint("provider", "provider_uid", name="uq_auth_provider_uid"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[AuthProviderType] = mapped_column(
        Enum(AuthProviderType), nullable=False, default=AuthProviderType.local
    )
    provider_uid: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="auth_providers")


class RefreshToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stored refresh token (hashed). Enables session revocation."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    device_hint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_expires_at", "expires_at"),
    )


# ─── Organisations ───────────────────────────────────────────
class Organisation(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A company / business on the platform. The core tenancy unit."""

    __tablename__ = "organisations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[OrganisationStatus] = mapped_column(
        Enum(OrganisationStatus), default=OrganisationStatus.active, nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    plan_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id"), nullable=True
    )

    # Business details
    company_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    vat_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="GBP", nullable=False)
    locale: Mapped[str] = mapped_column(String(10), default="en-GB", nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/London", nullable=False)
    address: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    plan: Mapped[Optional["Plan"]] = relationship(back_populates="organisations")
    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    roles: Mapped[list["Role"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    invitations: Mapped[list["Invitation"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    files: Mapped[list["File"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    settings: Mapped[list["OrganisationSetting"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    contacts: Mapped[list["Contact"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    payment_terms: Mapped[list["PaymentTerm"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    tax_rates: Mapped[list["TaxRate"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    invoice_sequences: Mapped[list["OrganisationInvoiceSequence"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    bill_sequences: Mapped[list["OrganisationBillSequence"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    bills: Mapped[list["Bill"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    captured_documents: Mapped[list["CapturedDocument"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    bank_accounts: Mapped[list["BankAccount"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    payment_sequences: Mapped[list["OrganisationPaymentSequence"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    accounts: Mapped[list["Account"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    journal_sequences: Mapped[list["OrganisationJournalSequence"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    journal_entries: Mapped[list["JournalEntry"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    financial_periods: Mapped[list["FinancialPeriod"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
    accounting_settings: Mapped[Optional["OrganisationAccountingSettings"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan", uselist=False
    )


    def __repr__(self) -> str:
        return f"<Organisation id={self.id} slug={self.slug}>"


# ─── Roles & Permissions ─────────────────────────────────────
class Permission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Fine-grained permission: resource + action pair.
    System permissions are seeded at startup.
    """

    __tablename__ = "permissions"
    __table_args__ = (UniqueConstraint("resource", "action", name="uq_permission_resource_action"),)

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    resource: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    role_permissions: Mapped[list["RolePermission"]] = relationship(back_populates="permission")


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A role within an organisation (or a system role if organisation_id is NULL).
    System roles: owner, admin, member, viewer.
    """

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    organisation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=True
    )
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    organisation: Mapped[Optional["Organisation"]] = relationship(back_populates="roles")
    role_permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
    memberships: Mapped[list["Membership"]] = relationship(back_populates="role")

    __table_args__ = (
        UniqueConstraint("organisation_id", "name", name="uq_role_org_name"),
        Index("ix_roles_organisation_id", "organisation_id"),
    )


class RolePermission(Base):
    """Many-to-many join: Role ↔ Permission."""

    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )

    role: Mapped["Role"] = relationship(back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship(back_populates="role_permissions")


# ─── Memberships ─────────────────────────────────────────────
class Membership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """User ↔ Organisation relationship with role assignment."""

    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organisation_id", name="uq_membership_user_org"),
        Index("ix_memberships_organisation_id", "organisation_id"),
        Index("ix_memberships_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False
    )
    status: Mapped[MembershipStatus] = mapped_column(
        Enum(MembershipStatus), default=MembershipStatus.active, nullable=False
    )
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="memberships")
    organisation: Mapped["Organisation"] = relationship(back_populates="memberships")
    role: Mapped["Role"] = relationship(back_populates="memberships")


# ─── Invitations ─────────────────────────────────────────────
class Invitation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Email-based invitation to join an organisation."""

    __tablename__ = "invitations"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    inviter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    status: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus), default=InvitationStatus.pending, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    organisation: Mapped["Organisation"] = relationship(back_populates="invitations")
    inviter: Mapped["User"] = relationship(
        back_populates="invitations_sent", foreign_keys=[inviter_id]
    )
    role: Mapped["Role"] = relationship()

    __table_args__ = (Index("ix_invitations_organisation_id", "organisation_id"),)


# ─── Audit Log ───────────────────────────────────────────────
class AuditLog(UUIDPrimaryKeyMixin, Base):
    """Immutable audit trail of all mutations in the system."""

    __tablename__ = "audit_logs"

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )

    # Context
    organisation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Event
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    diff: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Request context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    organisation: Mapped[Optional["Organisation"]] = relationship(back_populates="audit_logs")
    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_organisation_id", "organisation_id"),
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )


# ─── Files ───────────────────────────────────────────────────
class File(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Metadata record for every uploaded file."""

    __tablename__ = "files"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    uploaded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    key: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    organisation: Mapped["Organisation"] = relationship(back_populates="files")

    __table_args__ = (Index("ix_files_organisation_id", "organisation_id"),)


# ─── Settings ────────────────────────────────────────────────
class OrganisationSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Key-value settings store per organisation."""

    __tablename__ = "organisation_settings"
    __table_args__ = (
        UniqueConstraint("organisation_id", "key", name="uq_org_setting_key"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    organisation: Mapped["Organisation"] = relationship(back_populates="settings")


class UserNotificationPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """User-level notification preferences."""

    __tablename__ = "user_notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "notification_type", name="uq_user_notif_type"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notification_type: Mapped[str] = mapped_column(String(100), nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# ─── Payment Terms (Phase 2) ─────────────────────────────────
class PaymentTerm(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Reusable organisation-level payment terms."""

    __tablename__ = "payment_terms"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    term_type: Mapped[PaymentTermType] = mapped_column(
        Enum(PaymentTermType), default=PaymentTermType.DAYS_AFTER_INVOICE, nullable=False
    )
    days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_default_customer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_default_supplier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organisation: Mapped["Organisation"] = relationship(back_populates="payment_terms")
    contacts: Mapped[list["Contact"]] = relationship(back_populates="payment_terms")

    __table_args__ = (
        Index("ix_payment_terms_organisation_id", "organisation_id"),
        UniqueConstraint("organisation_id", "name", name="uq_payment_terms_org_name"),
    )


# ─── Contacts (Phase 2) ──────────────────────────────────────
class Contact(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Central business contact entity: Customer, Supplier, or Both."""

    __tablename__ = "contacts"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    contact_type: Mapped[ContactType] = mapped_column(
        Enum(ContactType), default=ContactType.CUSTOMER, nullable=False
    )
    status: Mapped[ContactStatus] = mapped_column(
        Enum(ContactStatus), default=ContactStatus.ACTIVE, nullable=False
    )

    business_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    legal_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    company_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    vat_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    tax_identifier: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    currency: Mapped[str] = mapped_column(String(3), default="GBP", nullable=False)
    payment_terms_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payment_terms.id", ondelete="SET NULL"), nullable=True
    )
    reference: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    credit_limit: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organisation: Mapped["Organisation"] = relationship(back_populates="contacts")
    payment_terms: Mapped[Optional["PaymentTerm"]] = relationship(back_populates="contacts")
    created_by: Mapped[Optional["User"]] = relationship()

    people: Mapped[list["ContactPerson"]] = relationship(
        back_populates="contact", cascade="all, delete-orphan", order_by="desc(ContactPerson.is_primary)"
    )
    addresses: Mapped[list["ContactAddress"]] = relationship(
        back_populates="contact", cascade="all, delete-orphan"
    )
    internal_notes: Mapped[list["ContactNote"]] = relationship(
        back_populates="contact", cascade="all, delete-orphan", order_by="desc(ContactNote.created_at)"
    )
    tags: Mapped[list["Tag"]] = relationship(
        secondary="contact_tags", back_populates="contacts"
    )
    bills: Mapped[list["Bill"]] = relationship(
        back_populates="supplier"
    )

    __table_args__ = (
        Index("ix_contacts_org_status", "organisation_id", "status"),
        Index("ix_contacts_org_type", "organisation_id", "contact_type"),
        Index("ix_contacts_org_business_name", "organisation_id", "business_name"),
        Index("ix_contacts_org_email", "organisation_id", "email"),
        Index("ix_contacts_org_company_number", "organisation_id", "company_number"),
        Index("ix_contacts_org_vat_number", "organisation_id", "vat_number"),
    )


# ─── Contact People ──────────────────────────────────────────
class ContactPerson(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Multiple contact persons per business contact."""

    __tablename__ = "contact_people"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    job_title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    contact: Mapped["Contact"] = relationship(back_populates="people")

    __table_args__ = (
        Index("ix_contact_people_contact_id", "contact_id"),
        Index("ix_contact_people_org_id", "organisation_id"),
    )


# ─── Contact Addresses ───────────────────────────────────────
class ContactAddress(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Multiple structured addresses per contact."""

    __tablename__ = "contact_addresses"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    address_type: Mapped[AddressType] = mapped_column(
        Enum(AddressType), default=AddressType.BILLING, nullable=False
    )
    line1: Mapped[str] = mapped_column(String(255), nullable=False)
    line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    county_region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postcode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country_code: Mapped[str] = mapped_column(String(2), default="GB", nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    contact: Mapped["Contact"] = relationship(back_populates="addresses")

    __table_args__ = (
        Index("ix_contact_addresses_contact_id", "contact_id"),
        Index("ix_contact_addresses_org_id", "organisation_id"),
    )


# ─── Contact Notes ───────────────────────────────────────────
class ContactNote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Internal notes attached to a contact."""

    __tablename__ = "contact_notes"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    contact: Mapped["Contact"] = relationship(back_populates="internal_notes")
    created_by: Mapped[Optional["User"]] = relationship()

    __table_args__ = (
        Index("ix_contact_notes_contact_id", "contact_id"),
        Index("ix_contact_notes_org_id", "organisation_id"),
    )


# ─── Polymorphic File Links (Attachments) ────────────────────
class FileLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Generic polymorphic attachment link for files attached to contacts, invoices, etc."""

    __tablename__ = "file_links"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "CONTACT", "INVOICE", etc.
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    file: Mapped["File"] = relationship()
    created_by: Mapped[Optional["User"]] = relationship()

    __table_args__ = (
        Index("ix_file_links_entity", "entity_type", "entity_id"),
        Index("ix_file_links_org_id", "organisation_id"),
    )


# ─── Tags (Phase 2) ──────────────────────────────────────────
class Tag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Organisational tags for contacts and future entities."""

    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("organisation_id", "name", name="uq_tag_org_name"),
        Index("ix_tags_organisation_id", "organisation_id"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#6366F1", nullable=False)

    contacts: Mapped[list["Contact"]] = relationship(
        secondary="contact_tags", back_populates="tags"
    )


class ContactTag(Base):
    """Many-to-many link: Contact ↔ Tag."""

    __tablename__ = "contact_tags"

    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )


# ─── Phase 3: Tax Rates ──────────────────────────────────────
class TaxRate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Configurable tax / VAT rates per organisation."""

    __tablename__ = "tax_rates"
    __table_args__ = (
        Index("ix_tax_rates_organisation_id", "organisation_id"),
        UniqueConstraint("organisation_id", "code", name="uq_tax_rate_org_code"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    rate: Mapped["Numeric"] = mapped_column(Numeric(8, 4), nullable=False)  # e.g. 20.0000
    tax_type: Mapped[TaxType] = mapped_column(
        Enum(TaxType), default=TaxType.STANDARD, nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    effective_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    organisation: Mapped["Organisation"] = relationship(back_populates="tax_rates")
    invoice_lines: Mapped[list["InvoiceLine"]] = relationship(back_populates="tax_rate")


# ─── Phase 3: Invoice Sequence ───────────────────────────────
class OrganisationInvoiceSequence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-organisation invoice number counter. Use FOR UPDATE row-locking."""

    __tablename__ = "organisation_invoice_sequences"
    __table_args__ = (
        UniqueConstraint("organisation_id", "prefix", name="uq_invoice_seq_org_prefix"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    prefix: Mapped[str] = mapped_column(String(20), default="INV-", nullable=False)
    next_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    padding: Mapped[int] = mapped_column(Integer, default=6, nullable=False)

    organisation: Mapped["Organisation"] = relationship(back_populates="invoice_sequences")


# ─── Phase 3: Invoices ───────────────────────────────────────
class Invoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Sales invoice header with immutable customer snapshot."""

    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("organisation_id", "invoice_number", name="uq_invoice_org_number"),
        Index("ix_invoices_org_status", "organisation_id", "status"),
        Index("ix_invoices_org_customer", "organisation_id", "customer_id"),
        Index("ix_invoices_org_issue_date", "organisation_id", "issue_date"),
        Index("ix_invoices_org_due_date", "organisation_id", "due_date"),
        Index("ix_invoices_org_number", "organisation_id", "invoice_number"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )

    # Invoice metadata
    invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False
    )
    issue_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="GBP", nullable=False)

    # References
    customer_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    purchase_order_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    payment_terms_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payment_terms.id", ondelete="SET NULL"), nullable=True
    )

    # ── Customer snapshot (immutable at approval) ────────────
    customer_name_snapshot: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_email_snapshot: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_vat_number_snapshot: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    billing_address_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # ── Financials (NUMERIC — never float) ──────────────────
    subtotal: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)
    discount_total: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)
    tax_total: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)
    total: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)
    amount_paid: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)
    amount_due: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)

    # ── Notes ───────────────────────────────────────────────
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)          # customer-visible
    terms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)          # customer-visible
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # internal only

    # ── Workflow fields ─────────────────────────────────────
    approved_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    void_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # ── Relationships ────────────────────────────────────────
    organisation: Mapped["Organisation"] = relationship(back_populates="invoices")
    customer: Mapped[Optional["Contact"]] = relationship()
    payment_terms: Mapped[Optional["PaymentTerm"]] = relationship()
    approved_by: Mapped[Optional["User"]] = relationship(foreign_keys=[approved_by_id])
    voided_by: Mapped[Optional["User"]] = relationship(foreign_keys=[voided_by_id])
    created_by: Mapped[Optional["User"]] = relationship(foreign_keys=[created_by_id])
    lines: Mapped[list["InvoiceLine"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLine.position",
    )
    deliveries: Mapped[list["InvoiceDelivery"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )
    allocations: Mapped[list["PaymentAllocation"]] = relationship(
        back_populates="invoice"
    )

    def __repr__(self) -> str:
        return f"<Invoice id={self.id} number={self.invoice_number} status={self.status}>"


# ─── Phase 3: Invoice Lines ──────────────────────────────────
class InvoiceLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Line-level detail on a sales invoice."""

    __tablename__ = "invoice_lines"
    __table_args__ = (
        Index("ix_invoice_lines_invoice_id", "invoice_id"),
        Index("ix_invoice_lines_org_id", "organisation_id"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    tax_rate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tax_rates.id", ondelete="SET NULL"), nullable=True
    )

    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped["Numeric"] = mapped_column(Numeric(19, 4), nullable=False)
    unit_price: Mapped["Numeric"] = mapped_column(Numeric(19, 4), nullable=False)

    # Discount
    discount_type: Mapped[Optional[DiscountType]] = mapped_column(
        Enum(DiscountType), nullable=True
    )
    discount_value: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)

    # Calculated (all backend-derived, stored for snapshot integrity)
    net_amount: Mapped["Numeric"] = mapped_column(Numeric(19, 4), nullable=False)
    tax_amount: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)
    gross_amount: Mapped["Numeric"] = mapped_column(Numeric(19, 4), nullable=False)

    # Tax rate snapshot at time of calculation
    tax_rate_snapshot: Mapped[Optional["Numeric"]] = mapped_column(Numeric(8, 4), nullable=True)

    invoice: Mapped["Invoice"] = relationship(back_populates="lines")
    tax_rate: Mapped[Optional["TaxRate"]] = relationship(back_populates="invoice_lines")


# ─── Phase 3: Invoice Deliveries ─────────────────────────────
class InvoiceDelivery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Audit record of every email send attempt for an invoice."""

    __tablename__ = "invoice_deliveries"
    __table_args__ = (
        Index("ix_invoice_deliveries_invoice_id", "invoice_id"),
        Index("ix_invoice_deliveries_org_id", "organisation_id"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    cc: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus), default=DeliveryStatus.QUEUED, nullable=False
    )
    sent_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    invoice: Mapped["Invoice"] = relationship(back_populates="deliveries")
    sent_by: Mapped[Optional["User"]] = relationship(foreign_keys=[sent_by_id])


# ─── Phase 4: Organisation Bill Sequence ────────────────────
class OrganisationBillSequence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-organisation bill number counter (e.g. BILL-000001). Concurrency-safe via row-locking."""

    __tablename__ = "organisation_bill_sequences"
    __table_args__ = (
        UniqueConstraint("organisation_id", "prefix", name="uq_bill_seq_org_prefix"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    prefix: Mapped[str] = mapped_column(String(20), default="BILL-", nullable=False)
    next_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    padding: Mapped[int] = mapped_column(Integer, default=6, nullable=False)

    organisation: Mapped["Organisation"] = relationship(back_populates="bill_sequences")


# ─── Phase 4: Bills ──────────────────────────────────────────
class Bill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Supplier bill / payable header with immutable supplier snapshot on approval."""

    __tablename__ = "bills"
    __table_args__ = (
        UniqueConstraint("organisation_id", "internal_bill_number", name="uq_bill_org_internal_number"),
        Index("ix_bills_org_status", "organisation_id", "status"),
        Index("ix_bills_org_supplier", "organisation_id", "supplier_id"),
        Index("ix_bills_org_bill_date", "organisation_id", "bill_date"),
        Index("ix_bills_org_due_date", "organisation_id", "due_date"),
        Index("ix_bills_org_supplier_inv_norm", "organisation_id", "supplier_invoice_number_normalized"),
        Index("ix_bills_org_internal_number", "organisation_id", "internal_bill_number"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )

    # Distinguish supplier's external invoice # from our platform's internal bill #
    supplier_invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
    supplier_invoice_number_normalized: Mapped[str] = mapped_column(String(100), nullable=False)
    internal_bill_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    status: Mapped[BillStatus] = mapped_column(
        Enum(BillStatus), default=BillStatus.DRAFT, nullable=False
    )
    bill_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="GBP", nullable=False)

    # References
    supplier_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    purchase_order_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    payment_terms_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payment_terms.id", ondelete="SET NULL"), nullable=True
    )

    # Category & Ledger integration readiness
    expense_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    purchase_category_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ── Supplier snapshot (immutable once approved) ──────────
    supplier_name_snapshot: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    supplier_email_snapshot: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    supplier_vat_number_snapshot: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    supplier_address_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # ── Financials (NUMERIC 19,4 — never float) ──────────────
    subtotal: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)
    discount_total: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)
    tax_total: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)
    total: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)
    amount_paid: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)
    amount_due: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)

    # ── Notes ───────────────────────────────────────────────
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Workflow & Approval tracking ────────────────────────
    submitted_for_approval_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    submitted_for_approval_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    voided_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    void_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Optimistic locking
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Duplicate override tracking
    duplicate_override_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    duplicate_override_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duplicate_override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Phase 5 — Smart Capture source traceability ──────────
    source_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("captured_documents.id", ondelete="SET NULL"), nullable=True
    )
    source_extraction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # ── Relationships ────────────────────────────────────────
    organisation: Mapped["Organisation"] = relationship(back_populates="bills")
    supplier: Mapped[Optional["Contact"]] = relationship(back_populates="bills")
    payment_terms: Mapped[Optional["PaymentTerm"]] = relationship()
    created_by: Mapped[Optional["User"]] = relationship(foreign_keys=[created_by_id])
    submitted_by: Mapped[Optional["User"]] = relationship(foreign_keys=[submitted_for_approval_by_id])
    approved_by: Mapped[Optional["User"]] = relationship(foreign_keys=[approved_by_id])
    rejected_by: Mapped[Optional["User"]] = relationship(foreign_keys=[rejected_by_id])
    voided_by: Mapped[Optional["User"]] = relationship(foreign_keys=[voided_by_id])
    duplicate_override_by: Mapped[Optional["User"]] = relationship(foreign_keys=[duplicate_override_by_id])

    lines: Mapped[list["BillLine"]] = relationship(
        back_populates="bill",
        cascade="all, delete-orphan",
        order_by="BillLine.position",
    )
    documents: Mapped[list["BillDocument"]] = relationship(
        back_populates="bill",
        cascade="all, delete-orphan",
    )
    approval_events: Mapped[list["BillApprovalEvent"]] = relationship(
        back_populates="bill",
        cascade="all, delete-orphan",
        order_by="BillApprovalEvent.created_at",
    )
    allocations: Mapped[list["PaymentAllocation"]] = relationship(
        back_populates="bill"
    )

    def __repr__(self) -> str:
        return f"<Bill id={self.id} internal={self.internal_bill_number} supplier_inv={self.supplier_invoice_number} status={self.status}>"


# ─── Phase 4: Bill Lines ─────────────────────────────────────
class BillLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Line-level detail on a supplier bill."""

    __tablename__ = "bill_lines"
    __table_args__ = (
        Index("ix_bill_lines_bill_id", "bill_id"),
        Index("ix_bill_lines_org_id", "organisation_id"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False
    )
    tax_rate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tax_rates.id", ondelete="SET NULL"), nullable=True
    )

    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped["Numeric"] = mapped_column(Numeric(19, 4), nullable=False)
    unit_price: Mapped["Numeric"] = mapped_column(Numeric(19, 4), nullable=False)

    # Discount
    discount_type: Mapped[Optional[DiscountType]] = mapped_column(
        Enum(DiscountType), nullable=True
    )
    discount_value: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)

    # Calculated (derived server-side via MoneyService)
    net_amount: Mapped["Numeric"] = mapped_column(Numeric(19, 4), nullable=False)
    tax_amount: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)
    gross_amount: Mapped["Numeric"] = mapped_column(Numeric(19, 4), nullable=False)

    # Tax rate snapshot at time of calculation
    tax_rate_snapshot: Mapped[Optional["Numeric"]] = mapped_column(Numeric(8, 4), nullable=True)

    # Accounting readiness
    expense_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    purchase_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    bill: Mapped["Bill"] = relationship(back_populates="lines")
    tax_rate: Mapped[Optional["TaxRate"]] = relationship()


# ─── Phase 4: Bill Documents ─────────────────────────────────
class BillDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Original supplier invoice and supporting document attachments with checksum integrity."""

    __tablename__ = "bill_documents"
    __table_args__ = (
        Index("ix_bill_documents_bill_id", "bill_id"),
        Index("ix_bill_documents_org_id", "organisation_id"),
        Index("ix_bill_documents_checksum", "organisation_id", "checksum_sha256"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(50), default="ORIGINAL_INVOICE", nullable=False)
    checksum_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    bill: Mapped["Bill"] = relationship(back_populates="documents")
    file: Mapped["File"] = relationship()
    created_by: Mapped[Optional["User"]] = relationship()


# ─── Phase 4: Bill Approval Events ───────────────────────────
class BillApprovalEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Workflow history tracking submission, approvals, and rejections."""

    __tablename__ = "bill_approval_events"
    __table_args__ = (
        Index("ix_bill_approval_events_bill_id", "bill_id"),
        Index("ix_bill_approval_events_org_id", "organisation_id"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False
    )
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[BillApprovalAction] = mapped_column(
        Enum(BillApprovalAction), nullable=False
    )
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    bill: Mapped["Bill"] = relationship(back_populates="approval_events")
    actor: Mapped[Optional["User"]] = relationship()


# ─── Phase 5: Smart Document Capture ─────────────────────────
class CapturedDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An uploaded invoice/receipt document awaiting or completing AI extraction."""

    __tablename__ = "captured_documents"
    __table_args__ = (
        Index("ix_captured_docs_org_status", "organisation_id", "processing_status"),
        Index("ix_captured_docs_org_checksum", "organisation_id", "checksum_sha256"),
        Index("ix_captured_docs_org_bill", "organisation_id", "created_bill_id"),
        Index("ix_captured_docs_org_created", "organisation_id", "created_at"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    # Link to platform File record (original file stored in object storage)
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("files.id", ondelete="RESTRICT"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Processing state machine
    processing_status: Mapped[DocumentProcessingStatus] = mapped_column(
        Enum(DocumentProcessingStatus),
        default=DocumentProcessingStatus.UPLOADED,
        nullable=False,
    )

    # Classification result
    document_type: Mapped[Optional[DocumentType]] = mapped_column(
        Enum(DocumentType), nullable=True
    )
    document_type_confidence: Mapped[Optional["Numeric"]] = mapped_column(
        Numeric(5, 4), nullable=True
    )

    # Points to the most recent (active) extraction
    current_extraction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    # Set once extraction creates a Phase 4 Bill
    created_bill_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bills.id", ondelete="SET NULL", use_alter=True), nullable=True
    )
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # User-correctable classification override
    user_document_type_override: Mapped[Optional[DocumentType]] = mapped_column(
        Enum(DocumentType), nullable=True
    )

    # ── Relationships ────────────────────────────────────────
    organisation: Mapped["Organisation"] = relationship(back_populates="captured_documents")
    file: Mapped["File"] = relationship()
    created_by: Mapped[Optional["User"]] = relationship(foreign_keys=[created_by_id])
    created_bill: Mapped[Optional["Bill"]] = relationship(foreign_keys=[created_bill_id])
    extractions: Mapped[list["DocumentExtraction"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentExtraction.created_at",
    )
    processing_jobs: Mapped[list["DocumentProcessingJob"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<CapturedDocument id={self.id} filename={self.original_filename} status={self.processing_status}>"


class DocumentExtraction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Structured AI/OCR extraction result for a captured document."""

    __tablename__ = "document_extractions"
    __table_args__ = (
        Index("ix_doc_extractions_document_id", "document_id"),
        Index("ix_doc_extractions_org_id", "organisation_id"),
        Index("ix_doc_extractions_supplier", "organisation_id", "matched_supplier_id"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("captured_documents.id", ondelete="CASCADE"), nullable=False
    )

    # Provider metadata
    provider: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "fake", "google_document_ai"
    provider_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Classification
    document_type: Mapped[Optional[DocumentType]] = mapped_column(
        Enum(DocumentType), nullable=True
    )
    document_type_confidence: Mapped[Optional["Numeric"]] = mapped_column(Numeric(5, 4), nullable=True)

    # Extracted supplier info
    supplier_name_raw: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    supplier_name_normalized: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    supplier_address_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    supplier_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    supplier_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    supplier_vat_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    supplier_company_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Extracted invoice fields
    invoice_number: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    invoice_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    purchase_order_number: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    reference: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)

    # Extracted financials (Numeric 19,4 — never float)
    subtotal: Mapped[Optional["Numeric"]] = mapped_column(Numeric(19, 4), nullable=True)
    discount_total: Mapped[Optional["Numeric"]] = mapped_column(Numeric(19, 4), nullable=True)
    tax_total: Mapped[Optional["Numeric"]] = mapped_column(Numeric(19, 4), nullable=True)
    total: Mapped[Optional["Numeric"]] = mapped_column(Numeric(19, 4), nullable=True)

    # Validation results
    math_valid: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    math_validation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tax_valid: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    date_valid: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Supplier match result
    matched_supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    matched_supplier_confidence: Mapped[Optional["Numeric"]] = mapped_column(Numeric(5, 4), nullable=True)
    supplier_match_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Duplicate detection result
    duplicate_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    duplicate_bill_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    duplicate_severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # LOW, MEDIUM, HIGH

    # Full raw provider output (for debugging / reprocessing)
    raw_extraction: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Processing timestamps
    processing_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processing_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # False when superseded by a reprocessing run
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Relationships ────────────────────────────────────────
    document: Mapped["CapturedDocument"] = relationship(back_populates="extractions")
    organisation: Mapped["Organisation"] = relationship()
    matched_supplier: Mapped[Optional["Contact"]] = relationship(
        foreign_keys=[matched_supplier_id]
    )
    fields: Mapped[list["DocumentExtractionField"]] = relationship(
        back_populates="extraction",
        cascade="all, delete-orphan",
        order_by="DocumentExtractionField.field_name",
    )
    lines: Mapped[list["DocumentExtractionLine"]] = relationship(
        back_populates="extraction",
        cascade="all, delete-orphan",
        order_by="DocumentExtractionLine.position",
    )

    def __repr__(self) -> str:
        return f"<DocumentExtraction id={self.id} provider={self.provider} invoice={self.invoice_number}>"


class DocumentExtractionField(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-field extraction detail: confidence, bounding box, correction tracking."""

    __tablename__ = "document_extraction_fields"
    __table_args__ = (
        Index("ix_doc_extract_fields_extraction", "extraction_id", "field_name"),
        Index("ix_doc_extract_fields_org", "organisation_id"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    extraction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_extractions.id", ondelete="CASCADE"), nullable=False
    )

    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional["Numeric"]] = mapped_column(Numeric(5, 4), nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Bounding box from OCR provider (format varies by provider, stored as JSONB)
    bounding_box: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # The surrounding OCR text (provenance context)
    source_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Correction tracking
    manually_corrected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    original_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # preserved before correction
    corrected_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    corrected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ────────────────────────────────────────
    extraction: Mapped["DocumentExtraction"] = relationship(back_populates="fields")
    corrected_by: Mapped[Optional["User"]] = relationship(foreign_keys=[corrected_by_id])


class DocumentExtractionLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Extracted line items from a supplier invoice."""

    __tablename__ = "document_extraction_lines"
    __table_args__ = (
        Index("ix_doc_extract_lines_extraction", "extraction_id", "position"),
        Index("ix_doc_extract_lines_org", "organisation_id"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    extraction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_extractions.id", ondelete="CASCADE"), nullable=False
    )

    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantity: Mapped[Optional["Numeric"]] = mapped_column(Numeric(19, 4), nullable=True)
    unit_price: Mapped[Optional["Numeric"]] = mapped_column(Numeric(19, 4), nullable=True)
    net_amount: Mapped[Optional["Numeric"]] = mapped_column(Numeric(19, 4), nullable=True)
    tax_rate: Mapped[Optional["Numeric"]] = mapped_column(Numeric(8, 4), nullable=True)
    tax_amount: Mapped[Optional["Numeric"]] = mapped_column(Numeric(19, 4), nullable=True)
    gross_amount: Mapped[Optional["Numeric"]] = mapped_column(Numeric(19, 4), nullable=True)

    confidence: Mapped[Optional["Numeric"]] = mapped_column(Numeric(5, 4), nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    manually_corrected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Relationships ────────────────────────────────────────
    extraction: Mapped["DocumentExtraction"] = relationship(back_populates="lines")


class DocumentProcessingJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """ARQ background job record for document processing pipeline stages."""

    __tablename__ = "document_processing_jobs"
    __table_args__ = (
        Index("ix_doc_proc_jobs_document", "document_id", "status"),
        Index("ix_doc_proc_jobs_org", "organisation_id"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("captured_documents.id", ondelete="CASCADE"), nullable=False
    )

    job_type: Mapped[str] = mapped_column(String(50), nullable=False)  # CLASSIFY, EXTRACT, VALIDATE
    status: Mapped[ExtractionJobStatus] = mapped_column(
        Enum(ExtractionJobStatus),
        default=ExtractionJobStatus.QUEUED,
        nullable=False,
    )
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provider_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # ── Relationships ────────────────────────────────────────
    document: Mapped["CapturedDocument"] = relationship(back_populates="processing_jobs")
    organisation: Mapped["Organisation"] = relationship()


class AIUsageEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """AI provider usage tracking for cost monitoring and future subscription billing."""

    __tablename__ = "ai_usage_events"
    __table_args__ = (
        Index("ix_ai_usage_org_created", "organisation_id", "created_at"),
        Index("ix_ai_usage_document", "document_id"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("captured_documents.id", ondelete="SET NULL"), nullable=True
    )
    extraction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    pages_processed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processing_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[Optional["Numeric"]] = mapped_column(Numeric(10, 6), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organisation: Mapped["Organisation"] = relationship()


# ─── Phase 6: Bank Accounts ──────────────────────────────────
class BankAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Company bank account for recording deposits, transfers, and disbursements."""

    __tablename__ = "bank_accounts"
    __table_args__ = (
        Index("ix_bank_accounts_org_id", "organisation_id"),
        UniqueConstraint("organisation_id", "account_name", name="uq_bank_account_org_name"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[BankAccountType] = mapped_column(
        Enum(BankAccountType), default=BankAccountType.CHECKING, nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="GBP", nullable=False)
    account_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sort_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    iban: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bic_swift: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    opening_balance: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)
    current_balance: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organisation: Mapped["Organisation"] = relationship(back_populates="bank_accounts")
    payments: Mapped[list["Payment"]] = relationship(back_populates="bank_account")


# ─── Phase 6: Payment Sequence ───────────────────────────────
class OrganisationPaymentSequence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-organisation payment number counter. Use FOR UPDATE row-locking."""

    __tablename__ = "organisation_payment_sequences"
    __table_args__ = (
        UniqueConstraint("organisation_id", "payment_type", name="uq_org_payment_sequence"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    payment_type: Mapped[PaymentType] = mapped_column(Enum(PaymentType), nullable=False)
    next_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    prefix: Mapped[str] = mapped_column(String(10), default="PAY-", nullable=False)

    organisation: Mapped["Organisation"] = relationship(back_populates="payment_sequences")


# ─── Phase 6: Payments ───────────────────────────────────────
class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Central payment entity for both Customer Money In and Supplier Money Out."""

    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_org_date", "organisation_id", "payment_date"),
        Index("ix_payments_contact", "contact_id"),
        Index("ix_payments_number", "organisation_id", "payment_number"),
        UniqueConstraint("organisation_id", "payment_number", name="uq_payments_org_number"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    payment_number: Mapped[str] = mapped_column(String(50), nullable=False)
    payment_type: Mapped[PaymentType] = mapped_column(Enum(PaymentType), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.POSTED, nullable=False
    )
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    bank_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True
    )

    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    amount: Mapped["Numeric"] = mapped_column(Numeric(19, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="GBP", nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod), default=PaymentMethod.BANK_TRANSFER, nullable=False
    )
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    allocated_amount: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)
    unallocated_amount: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    voided_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    void_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    organisation: Mapped["Organisation"] = relationship(back_populates="payments")
    contact: Mapped[Optional["Contact"]] = relationship()
    bank_account: Mapped[Optional["BankAccount"]] = relationship(back_populates="payments")
    allocations: Mapped[list["PaymentAllocation"]] = relationship(
        back_populates="payment",
        cascade="all, delete-orphan",
        order_by="PaymentAllocation.created_at",
    )
    created_by: Mapped[Optional["User"]] = relationship(foreign_keys=[created_by_id])
    voided_by: Mapped[Optional["User"]] = relationship(foreign_keys=[voided_by_id])


# ─── Phase 6: Payment Allocations ────────────────────────────
class PaymentAllocation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Line allocation of a Payment against an Invoice or Bill."""

    __tablename__ = "payment_allocations"
    __table_args__ = (
        Index("ix_payment_allocations_payment", "payment_id"),
        Index("ix_payment_allocations_invoice", "invoice_id"),
        Index("ix_payment_allocations_bill", "bill_id"),
        Index("ix_payment_allocations_org", "organisation_id"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id", ondelete="CASCADE"), nullable=False
    )
    target_type: Mapped[AllocationTargetType] = mapped_column(
        Enum(AllocationTargetType), nullable=False
    )
    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=True
    )
    bill_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bills.id", ondelete="CASCADE"), nullable=True
    )

    amount: Mapped["Numeric"] = mapped_column(Numeric(19, 4), nullable=False)
    allocated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    allocated_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    payment: Mapped["Payment"] = relationship(back_populates="allocations")
    invoice: Mapped[Optional["Invoice"]] = relationship(back_populates="allocations")
    bill: Mapped[Optional["Bill"]] = relationship(back_populates="allocations")
    allocated_by: Mapped[Optional["User"]] = relationship(foreign_keys=[allocated_by_id])


# ─── Phase 7: Chart of Accounts & General Ledger ─────────────
class Account(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Chart of Accounts ledger account."""

    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("organisation_id", "code", name="uq_account_org_code"),
        Index("ix_accounts_org_class", "organisation_id", "account_class"),
        Index("ix_accounts_org_active", "organisation_id", "active"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_class: Mapped[AccountClass] = mapped_column(Enum(AccountClass), nullable=False)
    account_subtype: Mapped[str] = mapped_column(String(50), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="GBP", nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    organisation: Mapped["Organisation"] = relationship(back_populates="accounts")
    journal_lines: Mapped[list["JournalLine"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


class OrganisationJournalSequence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Atomic sequence generator for journal entries per tenant."""

    __tablename__ = "organisation_journal_sequences"
    __table_args__ = (
        UniqueConstraint("organisation_id", "prefix", name="uq_journal_seq_org_prefix"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    prefix: Mapped[str] = mapped_column(String(20), default="JRN-", nullable=False)
    next_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    padding: Mapped[int] = mapped_column(Integer, default=6, nullable=False)

    organisation: Mapped["Organisation"] = relationship(back_populates="journal_sequences")


class JournalEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Double-entry journal header. Strict non-negotiable debits == credits."""

    __tablename__ = "journal_entries"
    __table_args__ = (
        UniqueConstraint("organisation_id", "entry_number", name="uq_journal_entry_org_number"),
        Index("ix_journal_entries_org_status", "organisation_id", "status"),
        Index("ix_journal_entries_org_date", "organisation_id", "entry_date"),
        Index("ix_journal_entries_org_source", "organisation_id", "source_type", "source_id"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    entry_number: Mapped[str] = mapped_column(String(50), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[JournalEntryStatus] = mapped_column(
        Enum(JournalEntryStatus), default=JournalEntryStatus.DRAFT, nullable=False
    )
    source_type: Mapped[JournalSourceType] = mapped_column(
        Enum(JournalSourceType), default=JournalSourceType.MANUAL, nullable=False
    )
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    narration: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Financials (Exact Decimal 19,4)
    total_debit: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)
    total_credit: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)

    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Reversal tracking
    reversed_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="SET NULL"), nullable=True
    )
    reversal_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    organisation: Mapped["Organisation"] = relationship(back_populates="journal_entries")
    lines: Mapped[list["JournalLine"]] = relationship(
        back_populates="journal_entry",
        cascade="all, delete-orphan",
        order_by="JournalLine.line_number",
    )
    posted_by: Mapped[Optional["User"]] = relationship(foreign_keys=[posted_by_id])
    reversed_entry: Mapped[Optional["JournalEntry"]] = relationship(
        foreign_keys=[reversed_entry_id], remote_side="JournalEntry.id"
    )


class JournalLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Single line of a double-entry journal (debit or credit)."""

    __tablename__ = "journal_lines"
    __table_args__ = (
        Index("ix_journal_lines_entry", "journal_entry_id"),
        Index("ix_journal_lines_account", "account_id"),
        Index("ix_journal_lines_contact", "contact_id"),
    )

    journal_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    line_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Debit and credit columns (NUMERIC 19,4)
    debit: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)
    credit: Mapped["Numeric"] = mapped_column(Numeric(19, 4), default=0, nullable=False)

    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    journal_entry: Mapped["JournalEntry"] = relationship(back_populates="lines")
    account: Mapped["Account"] = relationship(back_populates="journal_lines")
    contact: Mapped[Optional["Contact"]] = relationship()


class FinancialPeriod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Accounting period with lock status."""

    __tablename__ = "financial_periods"
    __table_args__ = (
        UniqueConstraint("organisation_id", "period_name", name="uq_financial_period_org_name"),
        Index("ix_financial_periods_dates", "organisation_id", "start_date", "end_date"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    period_name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    lock_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    organisation: Mapped["Organisation"] = relationship(back_populates="financial_periods")
    locked_by: Mapped[Optional["User"]] = relationship(foreign_keys=[locked_by_id])


class OrganisationAccountingSettings(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tenant accounting configuration and global period lock date."""

    __tablename__ = "organisation_accounting_settings"
    __table_args__ = (
        UniqueConstraint("organisation_id", name="uq_accounting_settings_org"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    financial_year_end_day: Mapped[int] = mapped_column(Integer, default=31, nullable=False)
    financial_year_end_month: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    lock_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    organisation: Mapped["Organisation"] = relationship(back_populates="accounting_settings")


