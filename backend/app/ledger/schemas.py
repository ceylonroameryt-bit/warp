"""
Warp Ladger — Phase 7 Accounting Ledger Pydantic Schemas
Strict Decimal validation, Chart of Accounts, Journal Entries, Period Locks, and Trial Balance.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.database.models import (
    AccountClass,
    AccountSubtype,
    JournalEntryStatus,
    JournalSourceType,
)


# ─── 1. Chart of Accounts (COA) ──────────────────────────────
class AccountBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=20, description="Account numeric code, e.g. '1200'")
    name: str = Field(..., min_length=1, max_length=255, description="Account title, e.g. 'Accounts Receivable'")
    account_class: AccountClass
    account_subtype: str = Field(..., min_length=1, max_length=50)
    currency: str = Field(default="GBP", min_length=3, max_length=3)
    description: Optional[str] = None


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    account_subtype: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    active: Optional[bool] = None


class AccountResponse(AccountBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organisation_id: UUID
    is_system: bool
    active: bool
    current_balance: Optional[Decimal] = Decimal("0.0000")
    created_at: datetime
    updated_at: datetime


# ─── 2. Journal Lines & Entries ──────────────────────────────
class JournalLineCreate(BaseModel):
    account_id: UUID
    description: Optional[str] = None
    debit: Decimal = Field(default=Decimal("0.0000"), ge=0)
    credit: Decimal = Field(default=Decimal("0.0000"), ge=0)
    contact_id: Optional[UUID] = None

    @field_validator("debit", "credit")
    @classmethod
    def validate_precision(cls, v: Decimal) -> Decimal:
        return Decimal(str(v)).quantize(Decimal("0.0001"))


class JournalLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    journal_entry_id: UUID
    account_id: UUID
    account_code: Optional[str] = None
    account_name: Optional[str] = None
    line_number: int
    description: Optional[str] = None
    debit: Decimal
    credit: Decimal
    contact_id: Optional[UUID] = None


class JournalEntryCreate(BaseModel):
    entry_date: date
    reference: Optional[str] = None
    narration: Optional[str] = None
    source_type: JournalSourceType = JournalSourceType.MANUAL
    source_id: Optional[UUID] = None
    lines: list[JournalLineCreate] = Field(..., min_length=2)
    post_immediately: bool = True

    @field_validator("lines")
    @classmethod
    def validate_double_entry_balance(cls, lines: list[JournalLineCreate]) -> list[JournalLineCreate]:
        total_dr = sum(l.debit for l in lines)
        total_cr = sum(l.credit for l in lines)
        if total_dr <= Decimal("0.0000") or total_cr <= Decimal("0.0000"):
            raise ValueError("Journal entry total debit and credit must be greater than zero.")
        if total_dr != total_cr:
            raise ValueError(
                f"Double-entry equation violated: total debits ({total_dr}) must equal total credits ({total_cr})."
            )
        for idx, l in enumerate(lines, 1):
            if l.debit > 0 and l.credit > 0:
                raise ValueError(f"Line {idx} cannot have both a debit and a credit amount.")
            if l.debit == 0 and l.credit == 0:
                raise ValueError(f"Line {idx} must have either a positive debit or credit amount.")
        return lines


class JournalEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organisation_id: UUID
    entry_number: str
    entry_date: date
    status: JournalEntryStatus
    source_type: JournalSourceType
    source_id: Optional[UUID] = None
    reference: Optional[str] = None
    narration: Optional[str] = None
    total_debit: Decimal
    total_credit: Decimal
    posted_at: Optional[datetime] = None
    posted_by_id: Optional[UUID] = None
    reversed_entry_id: Optional[UUID] = None
    reversal_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    lines: list[JournalLineResponse] = []


class JournalReverseRequest(BaseModel):
    reversal_reason: str = Field(..., min_length=3, max_length=500, description="Mandatory audit explanation for reversal")
    reversal_date: Optional[date] = Field(None, description="Date for the reversal entry; defaults to original entry date or today")


# ─── 3. Financial Periods & Period Locking ───────────────────
class FinancialPeriodCreate(BaseModel):
    period_name: str = Field(..., min_length=1, max_length=100)
    start_date: date
    end_date: date
    is_locked: bool = True
    lock_reason: Optional[str] = None


class FinancialPeriodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organisation_id: UUID
    period_name: str
    start_date: date
    end_date: date
    is_locked: bool
    locked_at: Optional[datetime] = None
    locked_by_id: Optional[UUID] = None
    lock_reason: Optional[str] = None
    created_at: datetime


class AccountingSettingsUpdate(BaseModel):
    financial_year_end_day: Optional[int] = Field(None, ge=1, le=31)
    financial_year_end_month: Optional[int] = Field(None, ge=1, le=12)
    lock_date: Optional[date] = None


class AccountingSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organisation_id: UUID
    financial_year_end_day: int
    financial_year_end_month: int
    lock_date: Optional[date] = None


# ─── 4. Reports: Trial Balance ────────────────────────────────
class TrialBalanceAccountItem(BaseModel):
    account_id: UUID
    account_code: str
    account_name: str
    account_class: AccountClass
    account_subtype: str
    debit_balance: Decimal
    credit_balance: Decimal


class TrialBalanceResponse(BaseModel):
    as_of_date: date
    currency: str
    accounts: list[TrialBalanceAccountItem]
    total_debit: Decimal
    total_credit: Decimal
    is_balanced: bool
