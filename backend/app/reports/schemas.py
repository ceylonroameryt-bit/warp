"""
Phase 8: Financial Reporting Pydantic V2 Schemas
Exact Decimal arithmetic for Profit & Loss, Balance Sheet, and Aged Debtors/Creditors
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class ReportLineItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: Optional[uuid.UUID] = None
    account_code: str
    account_name: str
    account_class: str
    subtype: Optional[str] = None
    amount: Decimal = Field(default=Decimal("0.0000"))
    comparison_amount: Optional[Decimal] = None
    variance: Optional[Decimal] = None
    variance_percentage: Optional[Decimal] = None


class ReportSection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    section_key: str
    title: str
    lines: list[ReportLineItem] = Field(default_factory=list)
    subtotal: Decimal = Field(default=Decimal("0.0000"))
    comparison_subtotal: Optional[Decimal] = None
    variance: Optional[Decimal] = None


class ProfitAndLossResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_date: date
    to_date: date
    comparison_from_date: Optional[date] = None
    comparison_to_date: Optional[date] = None
    turnover_section: ReportSection
    cogs_section: ReportSection
    operating_expenses_section: ReportSection
    turnover: Decimal
    cost_of_sales: Decimal
    gross_profit: Decimal
    operating_expenses: Decimal
    operating_profit: Decimal
    net_profit: Decimal
    comparison_gross_profit: Optional[Decimal] = None
    comparison_operating_profit: Optional[Decimal] = None
    comparison_net_profit: Optional[Decimal] = None
    currency: str = "GBP"
    generated_at: datetime


class BalanceSheetSection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    section_key: str
    title: str
    lines: list[ReportLineItem] = Field(default_factory=list)
    subtotal: Decimal = Field(default=Decimal("0.0000"))
    comparison_subtotal: Optional[Decimal] = None


class BalanceSheetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    as_of_date: date
    comparison_as_of_date: Optional[date] = None
    fixed_assets: BalanceSheetSection
    current_assets: BalanceSheetSection
    total_assets: Decimal
    current_liabilities: BalanceSheetSection
    non_current_liabilities: BalanceSheetSection
    total_liabilities: Decimal
    net_assets: Decimal
    equity: BalanceSheetSection
    current_year_earnings: Decimal
    total_equity: Decimal
    is_balanced: bool
    balance_discrepancy: Decimal
    currency: str = "GBP"
    generated_at: datetime


class AgedItemDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: uuid.UUID
    document_number: str
    reference: Optional[str] = None
    issue_date: date
    due_date: date
    days_overdue: int
    total_amount: Decimal
    paid_amount: Decimal
    remaining_balance: Decimal
    bucket: str  # "CURRENT", "DAYS_1_30", "DAYS_31_60", "DAYS_61_90", "DAYS_OVER_90"


class AgedContactSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contact_id: uuid.UUID
    contact_name: str
    company_number: Optional[str] = None
    currency: str = "GBP"
    current: Decimal = Field(default=Decimal("0.0000"))
    days_1_30: Decimal = Field(default=Decimal("0.0000"))
    days_31_60: Decimal = Field(default=Decimal("0.0000"))
    days_61_90: Decimal = Field(default=Decimal("0.0000"))
    days_over_90: Decimal = Field(default=Decimal("0.0000"))
    total: Decimal = Field(default=Decimal("0.0000"))
    items: list[AgedItemDetail] = Field(default_factory=list)


class AgedReportSummaryBuckets(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current: Decimal = Field(default=Decimal("0.0000"))
    days_1_30: Decimal = Field(default=Decimal("0.0000"))
    days_31_60: Decimal = Field(default=Decimal("0.0000"))
    days_61_90: Decimal = Field(default=Decimal("0.0000"))
    days_over_90: Decimal = Field(default=Decimal("0.0000"))
    grand_total: Decimal = Field(default=Decimal("0.0000"))


class AgedReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_type: str  # "RECEIVABLES" | "PAYABLES"
    as_of_date: date
    contacts: list[AgedContactSummary] = Field(default_factory=list)
    totals: AgedReportSummaryBuckets
    currency: str = "GBP"
    generated_at: datetime
