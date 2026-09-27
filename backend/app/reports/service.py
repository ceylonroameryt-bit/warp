"""
Phase 8: Financial Reporting Service
Implements Profit & Loss, Balance Sheet, Aged Receivables, and Aged Payables
using exact Decimal arithmetic and accounting standards.
"""

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Optional
import uuid

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.database.models import (
    Account,
    AccountClass,
    AccountSubtype,
    JournalEntry,
    JournalEntryStatus,
    JournalLine,
    Invoice,
    InvoiceStatus,
    Bill,
    BillStatus,
    Payment,
    PaymentStatus,
    PaymentAllocation,
    AllocationTargetType,
    Contact,
)
from app.reports.schemas import (
    ReportLineItem,
    ReportSection,
    ProfitAndLossResponse,
    BalanceSheetSection,
    BalanceSheetResponse,
    AgedItemDetail,
    AgedContactSummary,
    AgedReportSummaryBuckets,
    AgedReportResponse,
)

FOUR_PLACES = Decimal("0.0001")
TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0.0000")


def to_dec(val: any) -> Decimal:
    if val is None:
        return ZERO
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def quantize(val: Decimal) -> Decimal:
    return val.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)


class FinancialReportService:

    @staticmethod
    async def generate_profit_and_loss(
        db: AsyncSession,
        organisation_id: uuid.UUID,
        from_date: date,
        to_date: date,
        comparison_from_date: Optional[date] = None,
        comparison_to_date: Optional[date] = None,
    ) -> ProfitAndLossResponse:
        """
        Generates Profit & Loss (Income Statement) report for the given date range.
        Revenue: Credit - Debit
        Expense: Debit - Credit
        Gross Profit = Turnover - Cost of Sales
        Operating Profit = Gross Profit - Operating Expenses
        Net Profit = Operating Profit
        """
        # 1. Fetch all accounts for organisation
        acc_stmt = select(Account).where(
            Account.organisation_id == organisation_id,
            Account.account_class.in_([AccountClass.REVENUE, AccountClass.EXPENSE]),
        ).order_by(Account.code.asc())
        acc_res = await db.execute(acc_stmt)
        accounts = list(acc_res.scalars().all())

        # 2. Query journal lines for current period
        curr_stmt = (
            select(
                JournalLine.account_id,
                func.sum(JournalLine.debit).label("total_debit"),
                func.sum(JournalLine.credit).label("total_credit"),
            )
            .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
            .where(
                JournalEntry.organisation_id == organisation_id,
                JournalEntry.status == JournalEntryStatus.POSTED,
                JournalEntry.entry_date >= from_date,
                JournalEntry.entry_date <= to_date,
            )
            .group_by(JournalLine.account_id)
        )
        curr_res = await db.execute(curr_stmt)
        curr_map = {row.account_id: (to_dec(row.total_debit), to_dec(row.total_credit)) for row in curr_res}

        # 3. Query journal lines for comparison period (if provided)
        comp_map = {}
        if comparison_from_date and comparison_to_date:
            comp_stmt = (
                select(
                    JournalLine.account_id,
                    func.sum(JournalLine.debit).label("total_debit"),
                    func.sum(JournalLine.credit).label("total_credit"),
                )
                .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
                .where(
                    JournalEntry.organisation_id == organisation_id,
                    JournalEntry.status == JournalEntryStatus.POSTED,
                    JournalEntry.entry_date >= comparison_from_date,
                    JournalEntry.entry_date <= comparison_to_date,
                )
                .group_by(JournalLine.account_id)
            )
            comp_res = await db.execute(comp_stmt)
            comp_map = {row.account_id: (to_dec(row.total_debit), to_dec(row.total_credit)) for row in comp_res}

        turnover_lines: list[ReportLineItem] = []
        cogs_lines: list[ReportLineItem] = []
        opex_lines: list[ReportLineItem] = []

        total_turnover = ZERO
        total_cogs = ZERO
        total_opex = ZERO

        comp_turnover = ZERO if comp_map else None
        comp_cogs = ZERO if comp_map else None
        comp_opex = ZERO if comp_map else None

        for acc in accounts:
            curr_dr, curr_cr = curr_map.get(acc.id, (ZERO, ZERO))
            comp_dr, comp_cr = comp_map.get(acc.id, (ZERO, ZERO)) if comp_map else (None, None)

            if acc.account_class == AccountClass.REVENUE:
                curr_amt = quantize(curr_cr - curr_dr)
                comp_amt = quantize(comp_cr - comp_dr) if comp_map else None
            else:  # EXPENSE
                curr_amt = quantize(curr_dr - curr_cr)
                comp_amt = quantize(comp_dr - comp_cr) if comp_map else None

            # Skip accounts that have zero activity in both periods
            if curr_amt == ZERO and (comp_amt is None or comp_amt == ZERO):
                continue

            variance = quantize(curr_amt - comp_amt) if comp_amt is not None else None
            variance_pct = None
            if comp_amt is not None and comp_amt != ZERO:
                variance_pct = quantize(((curr_amt - comp_amt) / abs(comp_amt)) * Decimal("100.0"))

            item = ReportLineItem(
                account_id=acc.id,
                account_code=acc.code,
                account_name=acc.name,
                account_class=acc.account_class.value,
                subtype=acc.account_subtype if acc.account_subtype else None,
                amount=curr_amt,
                comparison_amount=comp_amt,
                variance=variance,
                variance_percentage=variance_pct,
            )

            if acc.account_class == AccountClass.REVENUE:
                turnover_lines.append(item)
                total_turnover += curr_amt
                if comp_amt is not None:
                    comp_turnover = (comp_turnover or ZERO) + comp_amt
            elif acc.account_subtype in ("COST_OF_SALES", "COST_OF_GOODS_SOLD"):
                cogs_lines.append(item)
                total_cogs += curr_amt
                if comp_amt is not None:
                    comp_cogs = (comp_cogs or ZERO) + comp_amt
            else:
                opex_lines.append(item)
                total_opex += curr_amt
                if comp_amt is not None:
                    comp_opex = (comp_opex or ZERO) + comp_amt

        gross_profit = quantize(total_turnover - total_cogs)
        operating_profit = quantize(gross_profit - total_opex)
        net_profit = operating_profit

        comp_gross = quantize(comp_turnover - comp_cogs) if comp_turnover is not None and comp_cogs is not None else None
        comp_op = quantize(comp_gross - comp_opex) if comp_gross is not None and comp_opex is not None else None
        comp_net = comp_op

        turnover_section = ReportSection(
            section_key="turnover",
            title="Turnover / Operating Revenue",
            lines=turnover_lines,
            subtotal=quantize(total_turnover),
            comparison_subtotal=quantize(comp_turnover) if comp_turnover is not None else None,
            variance=quantize(total_turnover - comp_turnover) if comp_turnover is not None else None,
        )

        cogs_section = ReportSection(
            section_key="cost_of_sales",
            title="Cost of Sales",
            lines=cogs_lines,
            subtotal=quantize(total_cogs),
            comparison_subtotal=quantize(comp_cogs) if comp_cogs is not None else None,
            variance=quantize(total_cogs - comp_cogs) if comp_cogs is not None else None,
        )

        opex_section = ReportSection(
            section_key="operating_expenses",
            title="Operating Expenses",
            lines=opex_lines,
            subtotal=quantize(total_opex),
            comparison_subtotal=quantize(comp_opex) if comp_opex is not None else None,
            variance=quantize(total_opex - comp_opex) if comp_opex is not None else None,
        )

        return ProfitAndLossResponse(
            from_date=from_date,
            to_date=to_date,
            comparison_from_date=comparison_from_date,
            comparison_to_date=comparison_to_date,
            turnover_section=turnover_section,
            cogs_section=cogs_section,
            operating_expenses_section=opex_section,
            turnover=quantize(total_turnover),
            cost_of_sales=quantize(total_cogs),
            gross_profit=gross_profit,
            operating_expenses=quantize(total_opex),
            operating_profit=operating_profit,
            net_profit=net_profit,
            comparison_gross_profit=comp_gross,
            comparison_operating_profit=comp_op,
            comparison_net_profit=comp_net,
            currency="GBP",
            generated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    async def generate_balance_sheet(
        db: AsyncSession,
        organisation_id: uuid.UUID,
        as_of_date: date,
        comparison_as_of_date: Optional[date] = None,
    ) -> BalanceSheetResponse:
        """
        Generates Balance Sheet (Statement of Financial Position) as at a given date.
        Total Assets = Total Liabilities + Total Equity
        Integrates Current Year Earnings (Cumulative Revenue - Cumulative Expense as at as_of_date).
        """
        # Fetch all accounts
        acc_stmt = select(Account).where(
            Account.organisation_id == organisation_id
        ).order_by(Account.code.asc())
        accounts = list((await db.execute(acc_stmt)).scalars().all())

        # Cumulative lines as of date
        curr_stmt = (
            select(
                JournalLine.account_id,
                func.sum(JournalLine.debit).label("total_debit"),
                func.sum(JournalLine.credit).label("total_credit"),
            )
            .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
            .where(
                JournalEntry.organisation_id == organisation_id,
                JournalEntry.status == JournalEntryStatus.POSTED,
                JournalEntry.entry_date <= as_of_date,
            )
            .group_by(JournalLine.account_id)
        )
        curr_res = await db.execute(curr_stmt)
        curr_map = {row.account_id: (to_dec(row.total_debit), to_dec(row.total_credit)) for row in curr_res}

        # Comparison cumulative lines (if provided)
        comp_map = {}
        if comparison_as_of_date:
            comp_stmt = (
                select(
                    JournalLine.account_id,
                    func.sum(JournalLine.debit).label("total_debit"),
                    func.sum(JournalLine.credit).label("total_credit"),
                )
                .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
                .where(
                    JournalEntry.organisation_id == organisation_id,
                    JournalEntry.status == JournalEntryStatus.POSTED,
                    JournalEntry.entry_date <= comparison_as_of_date,
                )
                .group_by(JournalLine.account_id)
            )
            comp_res = await db.execute(comp_stmt)
            comp_map = {row.account_id: (to_dec(row.total_debit), to_dec(row.total_credit)) for row in comp_res}

        fixed_asset_lines: list[ReportLineItem] = []
        current_asset_lines: list[ReportLineItem] = []
        current_liab_lines: list[ReportLineItem] = []
        non_current_liab_lines: list[ReportLineItem] = []
        equity_lines: list[ReportLineItem] = []

        total_fixed_assets = ZERO
        total_current_assets = ZERO
        total_current_liab = ZERO
        total_non_current_liab = ZERO
        total_historical_equity = ZERO

        # Also calculate cumulative revenue and expense up to as_of_date for Current Year Earnings
        cumulative_revenue = ZERO
        cumulative_expense = ZERO

        for acc in accounts:
            curr_dr, curr_cr = curr_map.get(acc.id, (ZERO, ZERO))
            comp_dr, comp_cr = comp_map.get(acc.id, (ZERO, ZERO)) if comp_map else (None, None)

            if acc.account_class == AccountClass.REVENUE:
                cumulative_revenue += (curr_cr - curr_dr)
                continue
            elif acc.account_class == AccountClass.EXPENSE:
                cumulative_expense += (curr_dr - curr_cr)
                continue

            # Asset: Debit - Credit
            if acc.account_class == AccountClass.ASSET:
                amt = quantize(curr_dr - curr_cr)
                comp_amt = quantize(comp_dr - comp_cr) if comp_map else None
                if amt == ZERO and (comp_amt is None or comp_amt == ZERO):
                    continue

                item = ReportLineItem(
                    account_id=acc.id,
                    account_code=acc.code,
                    account_name=acc.name,
                    account_class=acc.account_class.value,
                    subtype=acc.account_subtype if acc.account_subtype else None,
                    amount=amt,
                    comparison_amount=comp_amt,
                )

                if acc.account_subtype in ("FIXED_ASSET", "NON_CURRENT_ASSET"):
                    fixed_asset_lines.append(item)
                    total_fixed_assets += amt
                else:
                    current_asset_lines.append(item)
                    total_current_assets += amt

            # Liability: Credit - Debit
            elif acc.account_class == AccountClass.LIABILITY:
                amt = quantize(curr_cr - curr_dr)
                comp_amt = quantize(comp_cr - comp_dr) if comp_map else None
                if amt == ZERO and (comp_amt is None or comp_amt == ZERO):
                    continue

                item = ReportLineItem(
                    account_id=acc.id,
                    account_code=acc.code,
                    account_name=acc.name,
                    account_class=acc.account_class.value,
                    subtype=acc.account_subtype if acc.account_subtype else None,
                    amount=amt,
                    comparison_amount=comp_amt,
                )

                if acc.account_subtype in ("NON_CURRENT_LIABILITY", "LONG_TERM_LIABILITY"):
                    non_current_liab_lines.append(item)
                    total_non_current_liab += amt
                else:
                    current_liab_lines.append(item)
                    total_current_liab += amt

            # Equity: Credit - Debit
            elif acc.account_class == AccountClass.EQUITY:
                amt = quantize(curr_cr - curr_dr)
                comp_amt = quantize(comp_cr - comp_dr) if comp_map else None
                if amt == ZERO and (comp_amt is None or comp_amt == ZERO):
                    continue

                item = ReportLineItem(
                    account_id=acc.id,
                    account_code=acc.code,
                    account_name=acc.name,
                    account_class=acc.account_class.value,
                    subtype=acc.account_subtype if acc.account_subtype else None,
                    amount=amt,
                    comparison_amount=comp_amt,
                )
                equity_lines.append(item)
                total_historical_equity += amt

        # Current Year Earnings = Cumulative Net Profit (Revenue - Expense) as at as_of_date
        current_year_earnings = quantize(cumulative_revenue - cumulative_expense)

        total_assets = quantize(total_fixed_assets + total_current_assets)
        total_liabilities = quantize(total_current_liab + total_non_current_liab)
        net_assets = quantize(total_assets - total_liabilities)
        total_equity = quantize(total_historical_equity + current_year_earnings)

        discrepancy = quantize(total_assets - (total_liabilities + total_equity))
        is_balanced = abs(discrepancy) < Decimal("0.0001")

        fixed_assets_sec = BalanceSheetSection(
            section_key="fixed_assets",
            title="Fixed Assets (Non-Current)",
            lines=fixed_asset_lines,
            subtotal=quantize(total_fixed_assets),
        )

        current_assets_sec = BalanceSheetSection(
            section_key="current_assets",
            title="Current Assets",
            lines=current_asset_lines,
            subtotal=quantize(total_current_assets),
        )

        current_liab_sec = BalanceSheetSection(
            section_key="current_liabilities",
            title="Current Liabilities (Creditors: due within one year)",
            lines=current_liab_lines,
            subtotal=quantize(total_current_liab),
        )

        non_current_liab_sec = BalanceSheetSection(
            section_key="non_current_liabilities",
            title="Non-Current Liabilities (Creditors: due after one year)",
            lines=non_current_liab_lines,
            subtotal=quantize(total_non_current_liab),
        )

        equity_sec = BalanceSheetSection(
            section_key="equity",
            title="Capital & Reserves (Equity)",
            lines=equity_lines,
            subtotal=quantize(total_historical_equity),
        )

        return BalanceSheetResponse(
            as_of_date=as_of_date,
            comparison_as_of_date=comparison_as_of_date,
            fixed_assets=fixed_assets_sec,
            current_assets=current_assets_sec,
            total_assets=total_assets,
            current_liabilities=current_liab_sec,
            non_current_liabilities=non_current_liab_sec,
            total_liabilities=total_liabilities,
            net_assets=net_assets,
            equity=equity_sec,
            current_year_earnings=current_year_earnings,
            total_equity=total_equity,
            is_balanced=is_balanced,
            balance_discrepancy=discrepancy,
            currency="GBP",
            generated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    async def generate_aged_receivables(
        db: AsyncSession,
        organisation_id: uuid.UUID,
        as_of_date: date,
    ) -> AgedReportResponse:
        """
        Generates Aged Receivables (Debtors Aging) report as of a given date.
        Calculates remaining unpaid invoice amounts as of as_of_date and puts them into aging buckets.
        """
        as_of_dt = datetime.combine(as_of_date, datetime.max.time(), tzinfo=timezone.utc)
        stmt = (
            select(Invoice)
            .options(joinedload(Invoice.customer))
            .where(
                Invoice.organisation_id == organisation_id,
                Invoice.issue_date <= as_of_dt,
                Invoice.status.in_([
                    InvoiceStatus.APPROVED,
                    InvoiceStatus.SENT,
                    InvoiceStatus.PARTIALLY_PAID,
                    InvoiceStatus.PAID,
                ]),
            )
            .order_by(Invoice.issue_date.asc())
        )
        invoices = list((await db.execute(stmt)).scalars().all())

        # Fetch payments allocated to these invoices up to as_of_date
        invoice_ids = [inv.id for inv in invoices]
        paid_map: dict[uuid.UUID, Decimal] = {}
        if invoice_ids:
            alloc_stmt = (
                select(
                    PaymentAllocation.invoice_id,
                    func.sum(PaymentAllocation.amount).label("paid_sum"),
                )
                .join(Payment, PaymentAllocation.payment_id == Payment.id)
                .where(
                    PaymentAllocation.organisation_id == organisation_id,
                    PaymentAllocation.target_type == AllocationTargetType.INVOICE,
                    PaymentAllocation.invoice_id.in_(invoice_ids),
                    Payment.status == PaymentStatus.POSTED,
                    Payment.payment_date <= as_of_dt,
                )
                .group_by(PaymentAllocation.invoice_id)
            )
            alloc_res = await db.execute(alloc_stmt)
            paid_map = {row.invoice_id: to_dec(row.paid_sum) for row in alloc_res}

        contacts_map: dict[uuid.UUID, AgedContactSummary] = {}
        totals = AgedReportSummaryBuckets()

        for inv in invoices:
            total_amt = to_dec(getattr(inv, "total", getattr(inv, "total_gross", ZERO)))
            paid_amt = paid_map.get(inv.id, ZERO)
            remaining = quantize(total_amt - paid_amt)

            if remaining <= Decimal("0.0001"):
                continue  # Fully paid as of this date

            inv_due = inv.due_date.date() if isinstance(inv.due_date, datetime) else inv.due_date
            inv_issue = inv.issue_date.date() if isinstance(inv.issue_date, datetime) else inv.issue_date
            days_overdue = (as_of_date - inv_due).days
            if days_overdue <= 0:
                bucket = "CURRENT"
            elif days_overdue <= 30:
                bucket = "DAYS_1_30"
            elif days_overdue <= 60:
                bucket = "DAYS_31_60"
            elif days_overdue <= 90:
                bucket = "DAYS_61_90"
            else:
                bucket = "DAYS_OVER_90"

            item = AgedItemDetail(
                document_id=inv.id,
                document_number=inv.invoice_number or "",
                reference=inv.customer_reference or inv.purchase_order_reference,
                issue_date=inv_issue,
                due_date=inv_due,
                days_overdue=max(0, days_overdue),
                total_amount=quantize(total_amt),
                paid_amount=quantize(paid_amt),
                remaining_balance=remaining,
                bucket=bucket,
            )

            contact_id = inv.customer_id
            contact_name = inv.customer.business_name if inv.customer else (inv.customer_name_snapshot or "Unknown Customer")
            company_num = inv.customer.company_number if inv.customer else None

            if contact_id not in contacts_map:
                contacts_map[contact_id] = AgedContactSummary(
                    contact_id=contact_id,
                    contact_name=contact_name,
                    company_number=company_num,
                    currency=inv.currency or "GBP",
                )

            summary = contacts_map[contact_id]
            summary.items.append(item)
            summary.total = quantize(summary.total + remaining)
            totals.grand_total = quantize(totals.grand_total + remaining)

            if bucket == "CURRENT":
                summary.current = quantize(summary.current + remaining)
                totals.current = quantize(totals.current + remaining)
            elif bucket == "DAYS_1_30":
                summary.days_1_30 = quantize(summary.days_1_30 + remaining)
                totals.days_1_30 = quantize(totals.days_1_30 + remaining)
            elif bucket == "DAYS_31_60":
                summary.days_31_60 = quantize(summary.days_31_60 + remaining)
                totals.days_31_60 = quantize(totals.days_31_60 + remaining)
            elif bucket == "DAYS_61_90":
                summary.days_61_90 = quantize(summary.days_61_90 + remaining)
                totals.days_61_90 = quantize(totals.days_61_90 + remaining)
            else:
                summary.days_over_90 = quantize(summary.days_over_90 + remaining)
                totals.days_over_90 = quantize(totals.days_over_90 + remaining)

        sorted_contacts = sorted(contacts_map.values(), key=lambda c: c.contact_name)

        return AgedReportResponse(
            report_type="RECEIVABLES",
            as_of_date=as_of_date,
            contacts=sorted_contacts,
            totals=totals,
            currency="GBP",
            generated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    async def generate_aged_payables(
        db: AsyncSession,
        organisation_id: uuid.UUID,
        as_of_date: date,
    ) -> AgedReportResponse:
        """
        Generates Aged Payables (Creditors Aging) report as of a given date.
        Calculates remaining unpaid bill amounts as of as_of_date and puts them into aging buckets.
        """
        as_of_dt = datetime.combine(as_of_date, datetime.max.time(), tzinfo=timezone.utc)
        stmt = (
            select(Bill)
            .options(joinedload(Bill.supplier))
            .where(
                Bill.organisation_id == organisation_id,
                Bill.bill_date <= as_of_dt,
                Bill.status.in_([
                    BillStatus.APPROVED,
                    BillStatus.PARTIALLY_PAID,
                    BillStatus.PAID,
                ]),
            )
            .order_by(Bill.bill_date.asc())
        )
        bills = list((await db.execute(stmt)).scalars().all())

        # Fetch payments allocated to these bills up to as_of_date
        bill_ids = [b.id for b in bills]
        paid_map: dict[uuid.UUID, Decimal] = {}
        if bill_ids:
            alloc_stmt = (
                select(
                    PaymentAllocation.bill_id,
                    func.sum(PaymentAllocation.amount).label("paid_sum"),
                )
                .join(Payment, PaymentAllocation.payment_id == Payment.id)
                .where(
                    PaymentAllocation.organisation_id == organisation_id,
                    PaymentAllocation.target_type == AllocationTargetType.BILL,
                    PaymentAllocation.bill_id.in_(bill_ids),
                    Payment.status == PaymentStatus.POSTED,
                    Payment.payment_date <= as_of_dt,
                )
                .group_by(PaymentAllocation.bill_id)
            )
            alloc_res = await db.execute(alloc_stmt)
            paid_map = {row.bill_id: to_dec(row.paid_sum) for row in alloc_res}

        contacts_map: dict[uuid.UUID, AgedContactSummary] = {}
        totals = AgedReportSummaryBuckets()

        for bill in bills:
            total_amt = to_dec(getattr(bill, "total", getattr(bill, "total_gross", ZERO)))
            paid_amt = paid_map.get(bill.id, ZERO)
            remaining = quantize(total_amt - paid_amt)

            if remaining <= Decimal("0.0001"):
                continue  # Fully paid as of this date

            bill_due = bill.due_date.date() if isinstance(bill.due_date, datetime) else bill.due_date
            bill_issue = bill.bill_date.date() if isinstance(bill.bill_date, datetime) else bill.bill_date
            days_overdue = (as_of_date - bill_due).days
            if days_overdue <= 0:
                bucket = "CURRENT"
            elif days_overdue <= 30:
                bucket = "DAYS_1_30"
            elif days_overdue <= 60:
                bucket = "DAYS_31_60"
            elif days_overdue <= 90:
                bucket = "DAYS_61_90"
            else:
                bucket = "DAYS_OVER_90"

            item = AgedItemDetail(
                document_id=bill.id,
                document_number=bill.internal_bill_number or bill.supplier_invoice_number,
                reference=bill.supplier_reference or bill.purchase_order_reference,
                issue_date=bill_issue,
                due_date=bill_due,
                days_overdue=max(0, days_overdue),
                total_amount=quantize(total_amt),
                paid_amount=quantize(paid_amt),
                remaining_balance=remaining,
                bucket=bucket,
            )

            contact_id = bill.supplier_id
            contact_name = bill.supplier.business_name if bill.supplier else "Unknown Supplier"
            company_num = bill.supplier.company_number if bill.supplier else None

            if contact_id not in contacts_map:
                contacts_map[contact_id] = AgedContactSummary(
                    contact_id=contact_id,
                    contact_name=contact_name,
                    company_number=company_num,
                    currency=bill.currency or "GBP",
                )

            summary = contacts_map[contact_id]
            summary.items.append(item)
            summary.total = quantize(summary.total + remaining)
            totals.grand_total = quantize(totals.grand_total + remaining)

            if bucket == "CURRENT":
                summary.current = quantize(summary.current + remaining)
                totals.current = quantize(totals.current + remaining)
            elif bucket == "DAYS_1_30":
                summary.days_1_30 = quantize(summary.days_1_30 + remaining)
                totals.days_1_30 = quantize(totals.days_1_30 + remaining)
            elif bucket == "DAYS_31_60":
                summary.days_31_60 = quantize(summary.days_31_60 + remaining)
                totals.days_31_60 = quantize(totals.days_31_60 + remaining)
            elif bucket == "DAYS_61_90":
                summary.days_61_90 = quantize(summary.days_61_90 + remaining)
                totals.days_61_90 = quantize(totals.days_61_90 + remaining)
            else:
                summary.days_over_90 = quantize(summary.days_over_90 + remaining)
                totals.days_over_90 = quantize(totals.days_over_90 + remaining)

        sorted_contacts = sorted(contacts_map.values(), key=lambda c: c.contact_name)

        return AgedReportResponse(
            report_type="PAYABLES",
            as_of_date=as_of_date,
            contacts=sorted_contacts,
            totals=totals,
            currency="GBP",
            generated_at=datetime.now(timezone.utc),
        )
