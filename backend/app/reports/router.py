"""
Warp Ladger — Phase 8 Financial Reporting Router
REST endpoints for Profit & Loss, Balance Sheet, Aged Receivables, and Aged Payables.
All endpoints enforce multi-tenancy and 8-role RBAC permissions.
"""
from datetime import date
from decimal import Decimal
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import (
    CurrentUser,
    DBSession,
    OrgMembership,
    require_permission,
)
from app.reports.schemas import (
    ProfitAndLossResponse,
    BalanceSheetResponse,
    AgedReportResponse,
)
from app.reports.service import FinancialReportService

reports_router = APIRouter(
    prefix="/api/v1/organisations/{org_id}/reports",
    tags=["Financial Reporting"],
)


@reports_router.get(
    "/profit-and-loss",
    response_model=ProfitAndLossResponse,
    dependencies=[Depends(require_permission("reports", "profit_and_loss"))],
)
async def get_profit_and_loss(
    org_id: uuid.UUID,
    db: DBSession,
    from_date: Optional[date] = Query(None, description="Start date of the reporting period"),
    to_date: Optional[date] = Query(None, description="End date of the reporting period"),
    comparison_from_date: Optional[date] = Query(None, description="Comparison start date"),
    comparison_to_date: Optional[date] = Query(None, description="Comparison end date"),
):
    """
    Generate statutory Profit & Loss Statement (Income Statement) with exact decimal math,
    Turnover, Cost of Sales, Gross Profit, Operating Expenses, Operating Profit, and Net Profit.
    """
    today = date.today()
    f_date = from_date or date(today.year, 1, 1)
    t_date = to_date or today

    return await FinancialReportService.generate_profit_and_loss(
        db,
        organisation_id=org_id,
        from_date=f_date,
        to_date=t_date,
        comparison_from_date=comparison_from_date,
        comparison_to_date=comparison_to_date,
    )


@reports_router.get(
    "/balance-sheet",
    response_model=BalanceSheetResponse,
    dependencies=[Depends(require_permission("reports", "balance_sheet"))],
)
async def get_balance_sheet(
    org_id: uuid.UUID,
    db: DBSession,
    as_of_date: Optional[date] = Query(None, description="Snapshot date for the Balance Sheet"),
    comparison_as_of_date: Optional[date] = Query(None, description="Historical comparison snapshot date"),
):
    """
    Generate Statement of Financial Position (Balance Sheet) as at a specific date.
    Enforces equilibrium: Total Assets = Total Liabilities + Total Equity (including Current Year Earnings).
    """
    snapshot_date = as_of_date or date.today()
    return await FinancialReportService.generate_balance_sheet(
        db,
        organisation_id=org_id,
        as_of_date=snapshot_date,
        comparison_as_of_date=comparison_as_of_date,
    )


@reports_router.get(
    "/aged-receivables",
    response_model=AgedReportResponse,
    dependencies=[Depends(require_permission("reports", "aged_receivables"))],
)
async def get_aged_receivables(
    org_id: uuid.UUID,
    db: DBSession,
    as_of_date: Optional[date] = Query(None, description="Aging report as of date"),
):
    """
    Generate Aged Receivables (Debtors Aging) report.
    Breaks down outstanding unpaid invoices across standard aging buckets: Current, 1-30, 31-60, 61-90, 90+ days.
    """
    snapshot_date = as_of_date or date.today()
    return await FinancialReportService.generate_aged_receivables(
        db,
        organisation_id=org_id,
        as_of_date=snapshot_date,
    )


@reports_router.get(
    "/aged-payables",
    response_model=AgedReportResponse,
    dependencies=[Depends(require_permission("reports", "aged_payables"))],
)
async def get_aged_payables(
    org_id: uuid.UUID,
    db: DBSession,
    as_of_date: Optional[date] = Query(None, description="Aging report as of date"),
):
    """
    Generate Aged Payables (Creditors Aging) report.
    Breaks down outstanding unpaid bills across standard aging buckets: Current, 1-30, 31-60, 61-90, 90+ days.
    """
    snapshot_date = as_of_date or date.today()
    return await FinancialReportService.generate_aged_payables(
        db,
        organisation_id=org_id,
        as_of_date=snapshot_date,
    )


@reports_router.get(
    "/executive-summary",
    dependencies=[Depends(require_permission("reports", "view"))],
)
async def get_executive_summary(
    org_id: uuid.UUID,
    db: DBSession,
    as_of_date: Optional[date] = Query(None),
):
    """
    Executive financial overview metrics for the reporting hub dashboard.
    """
    today = as_of_date or date.today()
    start_of_year = date(today.year, 1, 1)

    pnl = await FinancialReportService.generate_profit_and_loss(
        db, organisation_id=org_id, from_date=start_of_year, to_date=today
    )
    bs = await FinancialReportService.generate_balance_sheet(
        db, organisation_id=org_id, as_of_date=today
    )
    ar = await FinancialReportService.generate_aged_receivables(
        db, organisation_id=org_id, as_of_date=today
    )
    ap = await FinancialReportService.generate_aged_payables(
        db, organisation_id=org_id, as_of_date=today
    )

    return {
        "as_of_date": today,
        "ytd_net_profit": pnl.net_profit,
        "ytd_turnover": pnl.turnover,
        "gross_profit_margin_pct": (
            ((pnl.gross_profit / pnl.turnover) * Decimal("100.0")).quantize(Decimal("0.01"))
            if pnl.turnover > Decimal("0.0001")
            else Decimal("0.00")
        ),
        "total_assets": bs.total_assets,
        "net_assets": bs.net_assets,
        "is_balance_sheet_balanced": bs.is_balanced,
        "debtors_outstanding": ar.totals.grand_total,
        "creditors_outstanding": ap.totals.grand_total,
        "currency": "GBP",
    }
