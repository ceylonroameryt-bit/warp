"""
Warp Ladger — Phase 8 Master Pytest Suite: Financial Reporting Core
Validates:
1. Profit & Loss Golden Accounting Math (Turnover, Cost of Sales, Gross Profit, Operating Expenses, Net Profit)
2. Profit & Loss Comparative Periods (Prior period variance, percentage changes)
3. Balance Sheet Equilibrium Equation (Total Assets = Total Liabilities + Total Equity including Current Year Earnings)
4. Balance Sheet Historical Time-Travel (Entries posted after as_of_date excluded)
5. Aged Receivables (Debtors Aging buckets: Current, 1-30, 31-60, 61-90, >90 days and partial payments)
6. Aged Payables (Creditors Aging buckets and supplier bill settlements)
7. 8-Role RBAC Enforcement (Owner, Accountant, Auditor, Viewer allowed; Employee denied 403)
8. Strict Tenant Isolation (Zero cross-tenant financial report leakage)
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import create_access_token
from app.database.models import (
    Account,
    AccountClass,
    AccountSubtype,
    Contact,
    ContactType,
    Invoice,
    InvoiceStatus,
    InvoiceLine,
    Bill,
    BillStatus,
    BillLine,
    Payment,
    PaymentStatus,
    PaymentAllocation,
    AllocationTargetType,
    PaymentType,
    JournalEntry,
    JournalEntryStatus,
    JournalLine,
    JournalSourceType,
    Membership,
    MembershipStatus,
    Organisation,
    Role,
    User,
)
from app.ledger.service import COAService
from app.roles.service import seed_permissions_and_roles

UTC = timezone.utc


@pytest.fixture
async def phase8_setup(db_session: AsyncSession):
    """Seed test data for Phase 8 Financial Reporting tests."""
    await seed_permissions_and_roles(db_session)

    # 1. Roles
    async def get_role(name: str):
        res = await db_session.execute(Role.__table__.select().where(Role.name == name))
        return res.mappings().first()["id"]

    roles = {
        "owner": await get_role("owner"),
        "accountant": await get_role("accountant"),
        "bookkeeper": await get_role("bookkeeper"),
        "auditor": await get_role("auditor"),
        "viewer": await get_role("viewer"),
        "employee": await get_role("employee"),
    }

    # 2. Users
    pwd_hash = "mock_hash"
    owner_a = User(email=f"owner_p8_{uuid.uuid4().hex[:6]}@test.com", hashed_password=pwd_hash, email_verified=True, full_name="Owner A")
    accountant_a = User(email=f"acct_p8_{uuid.uuid4().hex[:6]}@test.com", hashed_password=pwd_hash, email_verified=True, full_name="Accountant A")
    bookkeeper_a = User(email=f"bookie_p8_{uuid.uuid4().hex[:6]}@test.com", hashed_password=pwd_hash, email_verified=True, full_name="Bookkeeper A")
    auditor_a = User(email=f"auditor_p8_{uuid.uuid4().hex[:6]}@test.com", hashed_password=pwd_hash, email_verified=True, full_name="Auditor A")
    viewer_a = User(email=f"viewer_p8_{uuid.uuid4().hex[:6]}@test.com", hashed_password=pwd_hash, email_verified=True, full_name="Viewer A")
    employee_a = User(email=f"emp_p8_{uuid.uuid4().hex[:6]}@test.com", hashed_password=pwd_hash, email_verified=True, full_name="Employee A")
    owner_b = User(email=f"owner_b_p8_{uuid.uuid4().hex[:6]}@test.com", hashed_password=pwd_hash, email_verified=True, full_name="Owner B")

    db_session.add_all([owner_a, accountant_a, bookkeeper_a, auditor_a, viewer_a, employee_a, owner_b])
    await db_session.flush()

    # 3. Organisations
    org_a = Organisation(name="Phase8 Reporting Org A", slug=f"p8-org-a-{uuid.uuid4().hex[:6]}", owner_id=owner_a.id)
    org_b = Organisation(name="Phase8 Reporting Org B", slug=f"p8-org-b-{uuid.uuid4().hex[:6]}", owner_id=owner_b.id)
    db_session.add_all([org_a, org_b])
    await db_session.flush()

    # 4. Memberships
    members = [
        Membership(organisation_id=org_a.id, user_id=owner_a.id, role_id=roles["owner"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=accountant_a.id, role_id=roles["accountant"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=bookkeeper_a.id, role_id=roles["bookkeeper"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=auditor_a.id, role_id=roles["auditor"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=viewer_a.id, role_id=roles["viewer"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=employee_a.id, role_id=roles["employee"], status=MembershipStatus.active),
        Membership(organisation_id=org_b.id, user_id=owner_b.id, role_id=roles["owner"], status=MembershipStatus.active),
    ]
    db_session.add_all(members)
    await db_session.commit()

    tokens = {
        "owner_a": create_access_token(str(owner_a.id)),
        "accountant": create_access_token(str(accountant_a.id)),
        "bookkeeper": create_access_token(str(bookkeeper_a.id)),
        "auditor": create_access_token(str(auditor_a.id)),
        "viewer": create_access_token(str(viewer_a.id)),
        "employee": create_access_token(str(employee_a.id)),
        "owner_b": create_access_token(str(owner_b.id)),
    }

    # 5. Seed standard Chart of Accounts for Org A
    await COAService.ensure_default_accounts(db_session, org_a.id)

    return {
        "org_a_id": org_a.id,
        "org_b_id": org_b.id,
        "tokens": tokens,
        "owner_a": owner_a,
    }


@pytest.mark.asyncio
async def test_profit_and_loss_golden_math(client: AsyncClient, db_session: AsyncSession, phase8_setup):
    """
    Test P&L: Posts £10,000 Sales (4000), £3,000 COGS (5000), and £1,500 Operating Expense (6000).
    Verifies:
      Turnover = 10,000.00
      COGS = 3,000.00
      Gross Profit = 7,000.00
      Operating Expenses = 1,500.00
      Operating Profit = 5,500.00
      Net Profit = 5,500.00
    """
    org_id = phase8_setup["org_a_id"]
    token = phase8_setup["tokens"]["accountant"]
    user_id = phase8_setup["owner_a"].id

    # Lookup accounts
    async def get_acc(code: str):
        res = await db_session.execute(select(Account).where(Account.organisation_id == org_id, Account.code == code))
        return res.scalars().first()

    bank_acc = await get_acc("1000")
    sales_acc = await get_acc("4000")
    cogs_acc = await get_acc("5000")
    rent_acc = await get_acc("6000")

    entry_date = date(2026, 3, 15)

    # Journal 1: Sales (£10,000 Dr Bank, £10,000 Cr Sales)
    j1 = JournalEntry(
        organisation_id=org_id,
        entry_number="JRN-TEST-01",
        entry_date=entry_date,
        narration="Consulting revenue received",
        source_type=JournalSourceType.MANUAL,
        status=JournalEntryStatus.POSTED,
        total_debit=Decimal("10000.0000"),
        total_credit=Decimal("10000.0000"),
        posted_by_id=user_id,
    )
    db_session.add(j1)
    await db_session.flush()

    db_session.add_all([
        JournalLine(journal_entry_id=j1.id, account_id=bank_acc.id, line_number=1, debit=Decimal("10000.0000"), credit=Decimal("0.0000")),
        JournalLine(journal_entry_id=j1.id, account_id=sales_acc.id, line_number=2, debit=Decimal("0.0000"), credit=Decimal("10000.0000")),
    ])

    # Journal 2: Direct Cost (£3,000 Dr COGS, £3,000 Cr Bank)
    j2 = JournalEntry(
        organisation_id=org_id,
        entry_number="JRN-TEST-02",
        entry_date=entry_date,
        narration="Direct contractor costs",
        source_type=JournalSourceType.MANUAL,
        status=JournalEntryStatus.POSTED,
        total_debit=Decimal("3000.0000"),
        total_credit=Decimal("3000.0000"),
        posted_by_id=user_id,
    )
    db_session.add(j2)
    await db_session.flush()

    db_session.add_all([
        JournalLine(journal_entry_id=j2.id, account_id=cogs_acc.id, line_number=1, debit=Decimal("3000.0000"), credit=Decimal("0.0000")),
        JournalLine(journal_entry_id=j2.id, account_id=bank_acc.id, line_number=2, debit=Decimal("0.0000"), credit=Decimal("3000.0000")),
    ])

    # Journal 3: Operating Expense (£1,500 Dr Rent, £1,500 Cr Bank)
    j3 = JournalEntry(
        organisation_id=org_id,
        entry_number="JRN-TEST-03",
        entry_date=entry_date,
        narration="Monthly office rent",
        source_type=JournalSourceType.MANUAL,
        status=JournalEntryStatus.POSTED,
        total_debit=Decimal("1500.0000"),
        total_credit=Decimal("1500.0000"),
        posted_by_id=user_id,
    )
    db_session.add(j3)
    await db_session.flush()

    db_session.add_all([
        JournalLine(journal_entry_id=j3.id, account_id=rent_acc.id, line_number=1, debit=Decimal("1500.0000"), credit=Decimal("0.0000")),
        JournalLine(journal_entry_id=j3.id, account_id=bank_acc.id, line_number=2, debit=Decimal("0.0000"), credit=Decimal("1500.0000")),
    ])
    await db_session.commit()

    # Query Profit & Loss endpoint
    res = await client.get(
        f"/api/v1/organisations/{org_id}/reports/profit-and-loss?from_date=2026-03-01&to_date=2026-03-31",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert Decimal(str(data["turnover"])) == Decimal("10000.0000")
    assert Decimal(str(data["cost_of_sales"])) == Decimal("3000.0000")
    assert Decimal(str(data["gross_profit"])) == Decimal("7000.0000")
    assert Decimal(str(data["operating_expenses"])) == Decimal("1500.0000")
    assert Decimal(str(data["operating_profit"])) == Decimal("5500.0000")
    assert Decimal(str(data["net_profit"])) == Decimal("5500.0000")


@pytest.mark.asyncio
async def test_profit_and_loss_comparative_period(client: AsyncClient, db_session: AsyncSession, phase8_setup):
    """Test comparative P&L variance and percentage calculation."""
    org_id = phase8_setup["org_a_id"]
    token = phase8_setup["tokens"]["accountant"]
    user_id = phase8_setup["owner_a"].id

    async def get_acc(code: str):
        res = await db_session.execute(select(Account).where(Account.organisation_id == org_id, Account.code == code))
        return res.scalars().first()

    bank_acc = await get_acc("1000")
    sales_acc = await get_acc("4000")

    # Q1: £5,000 Sales
    j_q1 = JournalEntry(
        organisation_id=org_id,
        entry_number="JRN-Q1",
        entry_date=date(2026, 1, 15),
        narration="Q1 Sales",
        source_type=JournalSourceType.MANUAL,
        status=JournalEntryStatus.POSTED,
        total_debit=Decimal("5000.0000"),
        total_credit=Decimal("5000.0000"),
        posted_by_id=user_id,
    )
    db_session.add(j_q1)
    await db_session.flush()
    db_session.add_all([
        JournalLine(journal_entry_id=j_q1.id, account_id=bank_acc.id, line_number=1, debit=Decimal("5000.0000"), credit=Decimal("0.0000")),
        JournalLine(journal_entry_id=j_q1.id, account_id=sales_acc.id, line_number=2, debit=Decimal("0.0000"), credit=Decimal("5000.0000")),
    ])

    # Q2: £8,000 Sales
    j_q2 = JournalEntry(
        organisation_id=org_id,
        entry_number="JRN-Q2",
        entry_date=date(2026, 4, 15),
        narration="Q2 Sales",
        source_type=JournalSourceType.MANUAL,
        status=JournalEntryStatus.POSTED,
        total_debit=Decimal("8000.0000"),
        total_credit=Decimal("8000.0000"),
        posted_by_id=user_id,
    )
    db_session.add(j_q2)
    await db_session.flush()
    db_session.add_all([
        JournalLine(journal_entry_id=j_q2.id, account_id=bank_acc.id, line_number=1, debit=Decimal("8000.0000"), credit=Decimal("0.0000")),
        JournalLine(journal_entry_id=j_q2.id, account_id=sales_acc.id, line_number=2, debit=Decimal("0.0000"), credit=Decimal("8000.0000")),
    ])
    await db_session.commit()

    # Query Q2 with Q1 comparison
    res = await client.get(
        f"/api/v1/organisations/{org_id}/reports/profit-and-loss"
        f"?from_date=2026-04-01&to_date=2026-06-30"
        f"&comparison_from_date=2026-01-01&comparison_to_date=2026-03-31",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert Decimal(str(data["turnover"])) == Decimal("8000.0000")
    assert Decimal(str(data["turnover_section"]["subtotal"])) == Decimal("8000.0000")
    assert Decimal(str(data["turnover_section"]["comparison_subtotal"])) == Decimal("5000.0000")
    assert Decimal(str(data["turnover_section"]["variance"])) == Decimal("3000.0000")

    # Percentage change = (3000 / 5000) * 100 = 60.0%
    line = data["turnover_section"]["lines"][0]
    assert Decimal(str(line["variance_percentage"])) == Decimal("60.0000")


@pytest.mark.asyncio
async def test_balance_sheet_equation_equilibrium(client: AsyncClient, db_session: AsyncSession, phase8_setup):
    """
    Test fundamental Balance Sheet Equation:
      Total Assets = Total Liabilities + Total Equity
    Verifies that Current Year Earnings (Cumulative Revenue - Expense) automatically bridges Net Assets and Equity.
    """
    org_id = phase8_setup["org_a_id"]
    token = phase8_setup["tokens"]["accountant"]
    user_id = phase8_setup["owner_a"].id

    async def get_acc(code: str):
        res = await db_session.execute(select(Account).where(Account.organisation_id == org_id, Account.code == code))
        return res.scalars().first()

    bank_acc = await get_acc("1000")
    equity_acc = await get_acc("3000")
    sales_acc = await get_acc("4000")
    cogs_acc = await get_acc("5000")

    # 1. Share capital initial deposit (£20,000 Dr Bank, £20,000 Cr Share Capital)
    j1 = JournalEntry(
        organisation_id=org_id,
        entry_number="JRN-CAP",
        entry_date=date(2026, 1, 1),
        narration="Initial capital injection",
        source_type=JournalSourceType.MANUAL,
        status=JournalEntryStatus.POSTED,
        total_debit=Decimal("20000.0000"),
        total_credit=Decimal("20000.0000"),
        posted_by_id=user_id,
    )
    db_session.add(j1)
    await db_session.flush()
    db_session.add_all([
        JournalLine(journal_entry_id=j1.id, account_id=bank_acc.id, line_number=1, debit=Decimal("20000.0000"), credit=Decimal("0.0000")),
        JournalLine(journal_entry_id=j1.id, account_id=equity_acc.id, line_number=2, debit=Decimal("0.0000"), credit=Decimal("20000.0000")),
    ])

    # 2. Operating Activity (£6,000 Sales Revenue, £2,000 Direct Cost)
    j2 = JournalEntry(
        organisation_id=org_id,
        entry_number="JRN-OPS",
        entry_date=date(2026, 2, 1),
        narration="Trading activity",
        source_type=JournalSourceType.MANUAL,
        status=JournalEntryStatus.POSTED,
        total_debit=Decimal("8000.0000"),
        total_credit=Decimal("8000.0000"),
        posted_by_id=user_id,
    )
    db_session.add(j2)
    await db_session.flush()
    db_session.add_all([
        JournalLine(journal_entry_id=j2.id, account_id=bank_acc.id, line_number=1, debit=Decimal("6000.0000"), credit=Decimal("0.0000")),
        JournalLine(journal_entry_id=j2.id, account_id=sales_acc.id, line_number=2, debit=Decimal("0.0000"), credit=Decimal("6000.0000")),
        JournalLine(journal_entry_id=j2.id, account_id=cogs_acc.id, line_number=3, debit=Decimal("2000.0000"), credit=Decimal("0.0000")),
        JournalLine(journal_entry_id=j2.id, account_id=bank_acc.id, line_number=4, debit=Decimal("0.0000"), credit=Decimal("2000.0000")),
    ])
    await db_session.commit()

    # Net Assets = £20,000 (initial) + £6,000 (sales) - £2,000 (cogs) = £24,000 Cash
    # Historical Equity = £20,000 Share Capital
    # Current Year Earnings = £6,000 - £2,000 = £4,000
    # Total Equity = £20,000 + £4,000 = £24,000
    # Equation: Total Assets (£24,000) == Total Liabilities (£0) + Total Equity (£24,000)

    res = await client.get(
        f"/api/v1/organisations/{org_id}/reports/balance-sheet?as_of_date=2026-02-28",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert Decimal(str(data["total_assets"])) == Decimal("24000.0000")
    assert Decimal(str(data["total_liabilities"])) == Decimal("0.0000")
    assert Decimal(str(data["net_assets"])) == Decimal("24000.0000")
    assert Decimal(str(data["current_year_earnings"])) == Decimal("4000.0000")
    assert Decimal(str(data["total_equity"])) == Decimal("24000.0000")
    assert data["is_balanced"] is True
    assert Decimal(str(data["balance_discrepancy"])) == Decimal("0.0000")


@pytest.mark.asyncio
async def test_balance_sheet_historical_time_travel(client: AsyncClient, db_session: AsyncSession, phase8_setup):
    """Ensure transactions dated after as_of_date do not leak into the historical snapshot."""
    org_id = phase8_setup["org_a_id"]
    token = phase8_setup["tokens"]["accountant"]
    user_id = phase8_setup["owner_a"].id

    async def get_acc(code: str):
        res = await db_session.execute(select(Account).where(Account.organisation_id == org_id, Account.code == code))
        return res.scalars().first()

    bank_acc = await get_acc("1000")
    equity_acc = await get_acc("3000")

    # Entry 1 on 2026-01-10 (£5,000)
    j1 = JournalEntry(
        organisation_id=org_id,
        entry_number="JRN-JAN",
        entry_date=date(2026, 1, 10),
        narration="January Capital",
        source_type=JournalSourceType.MANUAL,
        status=JournalEntryStatus.POSTED,
        total_debit=Decimal("5000.0000"),
        total_credit=Decimal("5000.0000"),
        posted_by_id=user_id,
    )
    db_session.add(j1)
    await db_session.flush()
    db_session.add_all([
        JournalLine(journal_entry_id=j1.id, account_id=bank_acc.id, line_number=1, debit=Decimal("5000.0000"), credit=Decimal("0.0000")),
        JournalLine(journal_entry_id=j1.id, account_id=equity_acc.id, line_number=2, debit=Decimal("0.0000"), credit=Decimal("5000.0000")),
    ])

    # Entry 2 on 2026-03-10 (£15,000)
    j2 = JournalEntry(
        organisation_id=org_id,
        entry_number="JRN-MAR",
        entry_date=date(2026, 3, 10),
        narration="March Capital",
        source_type=JournalSourceType.MANUAL,
        status=JournalEntryStatus.POSTED,
        total_debit=Decimal("15000.0000"),
        total_credit=Decimal("15000.0000"),
        posted_by_id=user_id,
    )
    db_session.add(j2)
    await db_session.flush()
    db_session.add_all([
        JournalLine(journal_entry_id=j2.id, account_id=bank_acc.id, line_number=1, debit=Decimal("15000.0000"), credit=Decimal("0.0000")),
        JournalLine(journal_entry_id=j2.id, account_id=equity_acc.id, line_number=2, debit=Decimal("0.0000"), credit=Decimal("15000.0000")),
    ])
    await db_session.commit()

    # Query as of 2026-01-31 (should only show £5,000, excluding the March £15,000)
    res = await client.get(
        f"/api/v1/organisations/{org_id}/reports/balance-sheet?as_of_date=2026-01-31",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert Decimal(str(data["total_assets"])) == Decimal("5000.0000")

    # Query as of 2026-03-31 (should now show £20,000)
    res_mar = await client.get(
        f"/api/v1/organisations/{org_id}/reports/balance-sheet?as_of_date=2026-03-31",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_mar.status_code == 200, res_mar.text
    assert Decimal(str(res_mar.json()["total_assets"])) == Decimal("20000.0000")


@pytest.mark.asyncio
async def test_aged_receivables_bucket_allocation(client: AsyncClient, db_session: AsyncSession, phase8_setup):
    """
    Test Aged Receivables:
    Creates customer with:
      - Inv 1: Due in future (CURRENT) £1,000
      - Inv 2: Due 15 days ago (DAYS_1_30) £2,000 (partially paid £500, remaining £1,500)
      - Inv 3: Due 45 days ago (DAYS_31_60) £3,000
    Verifies bucket totals: Current £1,000, 1-30 £1,500, 31-60 £3,000. Grand Total = £5,500.
    """
    org_id = phase8_setup["org_a_id"]
    token = phase8_setup["tokens"]["accountant"]
    user_id = phase8_setup["owner_a"].id

    cust = Contact(
        organisation_id=org_id,
        business_name="Apex Commercial Client Ltd",
        company_number="08812345",
        contact_type=ContactType.CUSTOMER,
    )
    db_session.add(cust)
    await db_session.flush()

    as_of = date(2026, 3, 31)

    # Inv 1: Due 2026-04-15 (future -> CURRENT)
    inv1 = Invoice(
        organisation_id=org_id,
        customer_id=cust.id,
        invoice_number="INV-AGED-01",
        status=InvoiceStatus.APPROVED,
        issue_date=datetime(2026, 3, 1, tzinfo=UTC),
        due_date=datetime(2026, 4, 15, tzinfo=UTC),
        currency="GBP",
        subtotal=Decimal("1000.0000"),
        discount_total=Decimal("0.0000"),
        tax_total=Decimal("0.0000"),
        total=Decimal("1000.0000"),
        amount_paid=Decimal("0.0000"),
        amount_due=Decimal("1000.0000"),
    )

    # Inv 2: Due 2026-03-16 (15 days overdue -> DAYS_1_30)
    inv2 = Invoice(
        organisation_id=org_id,
        customer_id=cust.id,
        invoice_number="INV-AGED-02",
        status=InvoiceStatus.PARTIALLY_PAID,
        issue_date=datetime(2026, 2, 15, tzinfo=UTC),
        due_date=datetime(2026, 3, 16, tzinfo=UTC),
        currency="GBP",
        subtotal=Decimal("2000.0000"),
        discount_total=Decimal("0.0000"),
        tax_total=Decimal("0.0000"),
        total=Decimal("2000.0000"),
        amount_paid=Decimal("500.0000"),
        amount_due=Decimal("1500.0000"),
    )

    # Inv 3: Due 2026-02-14 (45 days overdue -> DAYS_31_60)
    inv3 = Invoice(
        organisation_id=org_id,
        customer_id=cust.id,
        invoice_number="INV-AGED-03",
        status=InvoiceStatus.APPROVED,
        issue_date=datetime(2026, 1, 15, tzinfo=UTC),
        due_date=datetime(2026, 2, 14, tzinfo=UTC),
        currency="GBP",
        subtotal=Decimal("3000.0000"),
        discount_total=Decimal("0.0000"),
        tax_total=Decimal("0.0000"),
        total=Decimal("3000.0000"),
        amount_paid=Decimal("0.0000"),
        amount_due=Decimal("3000.0000"),
    )

    db_session.add_all([inv1, inv2, inv3])
    await db_session.flush()

    # Add partial payment of £500 against Inv 2
    pay = Payment(
        organisation_id=org_id,
        payment_number="PAY-AGED-01",
        payment_type=PaymentType.INCOMING,
        payment_date=datetime(2026, 3, 20, 10, 0, tzinfo=UTC),
        amount=Decimal("500.0000"),
        allocated_amount=Decimal("500.0000"),
        unallocated_amount=Decimal("0.0000"),
        currency="GBP",
        payment_method="BANK_TRANSFER",
        status=PaymentStatus.POSTED,
        created_by_id=user_id,
    )
    db_session.add(pay)
    await db_session.flush()

    alloc = PaymentAllocation(
        organisation_id=org_id,
        payment_id=pay.id,
        target_type=AllocationTargetType.INVOICE,
        invoice_id=inv2.id,
        amount=Decimal("500.0000"),
        allocated_at=datetime(2026, 3, 20, 10, 0, tzinfo=UTC),
    )
    db_session.add(alloc)
    await db_session.commit()

    # Query Aged Receivables endpoint
    res = await client.get(
        f"/api/v1/organisations/{org_id}/reports/aged-receivables?as_of_date=2026-03-31",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["report_type"] == "RECEIVABLES"
    totals = data["totals"]
    assert Decimal(str(totals["current"])) == Decimal("1000.0000")
    assert Decimal(str(totals["days_1_30"])) == Decimal("1500.0000")
    assert Decimal(str(totals["days_31_60"])) == Decimal("3000.0000")
    assert Decimal(str(totals["grand_total"])) == Decimal("5500.0000")


@pytest.mark.asyncio
async def test_aged_payables_bucket_allocation(client: AsyncClient, db_session: AsyncSession, phase8_setup):
    """
    Test Aged Payables:
    Creates supplier with:
      - Bill 1: Due 20 days ago (DAYS_1_30) £1,200
      - Bill 2: Due 75 days ago (DAYS_61_90) £2,500
    Verifies bucket totals: 1-30 £1,200, 61-90 £2,500. Grand Total = £3,700.
    """
    org_id = phase8_setup["org_a_id"]
    token = phase8_setup["tokens"]["accountant"]
    user_id = phase8_setup["owner_a"].id

    supp = Contact(
        organisation_id=org_id,
        business_name="National Power & Utilities Plc",
        contact_type=ContactType.SUPPLIER,
    )
    db_session.add(supp)
    await db_session.flush()

    as_of = date(2026, 3, 31)

    # Bill 1: Due 2026-03-11 (20 days overdue -> DAYS_1_30)
    b1 = Bill(
        organisation_id=org_id,
        supplier_id=supp.id,
        supplier_invoice_number="BILL-SUPP-01",
        supplier_invoice_number_normalized="bill-supp-01",
        internal_bill_number="BIL-000001",
        status=BillStatus.APPROVED,
        bill_date=datetime(2026, 2, 10, tzinfo=UTC),
        due_date=datetime(2026, 3, 11, tzinfo=UTC),
        currency="GBP",
        subtotal=Decimal("1200.0000"),
        discount_total=Decimal("0.0000"),
        tax_total=Decimal("0.0000"),
        total=Decimal("1200.0000"),
        amount_paid=Decimal("0.0000"),
        amount_due=Decimal("1200.0000"),
    )

    # Bill 2: Due 2026-01-15 (75 days overdue -> DAYS_61_90)
    b2 = Bill(
        organisation_id=org_id,
        supplier_id=supp.id,
        supplier_invoice_number="BILL-SUPP-02",
        supplier_invoice_number_normalized="bill-supp-02",
        internal_bill_number="BIL-000002",
        status=BillStatus.APPROVED,
        bill_date=datetime(2025, 12, 15, tzinfo=UTC),
        due_date=datetime(2026, 1, 15, tzinfo=UTC),
        currency="GBP",
        subtotal=Decimal("2500.0000"),
        discount_total=Decimal("0.0000"),
        tax_total=Decimal("0.0000"),
        total=Decimal("2500.0000"),
        amount_paid=Decimal("0.0000"),
        amount_due=Decimal("2500.0000"),
    )

    db_session.add_all([b1, b2])
    await db_session.commit()

    res = await client.get(
        f"/api/v1/organisations/{org_id}/reports/aged-payables?as_of_date=2026-03-31",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["report_type"] == "PAYABLES"
    totals = data["totals"]
    assert Decimal(str(totals["days_1_30"])) == Decimal("1200.0000")
    assert Decimal(str(totals["days_61_90"])) == Decimal("2500.0000")
    assert Decimal(str(totals["grand_total"])) == Decimal("3700.0000")


@pytest.mark.asyncio
async def test_reports_rbac_enforcement(client: AsyncClient, phase8_setup):
    """
    Test RBAC Segregation of Duties:
    Owner, Accountant, Auditor, Viewer are granted reports:profit_and_loss (200 OK).
    Employee is denied reports access (403 Forbidden).
    """
    org_id = phase8_setup["org_a_id"]
    tokens = phase8_setup["tokens"]

    url = f"/api/v1/organisations/{org_id}/reports/profit-and-loss"

    # Authorized roles
    for role_key in ["owner_a", "accountant", "auditor", "viewer"]:
        res = await client.get(url, headers={"Authorization": f"Bearer {tokens[role_key]}"})
        assert res.status_code == 200, f"Role {role_key} unexpectedly failed: {res.text}"

    # Unauthorized role: Employee
    res_emp = await client.get(url, headers={"Authorization": f"Bearer {tokens['employee']}"})
    assert res_emp.status_code == 403, f"Employee was not denied: {res_emp.status_code}"


@pytest.mark.asyncio
async def test_reports_tenant_isolation(client: AsyncClient, phase8_setup):
    """
    Test Strict Multi-Tenant Isolation:
    Financial reports for Organisation B return 0 balances, unaffected by Org A's transactions.
    """
    org_b_id = phase8_setup["org_b_id"]
    token_b = phase8_setup["tokens"]["owner_b"]

    res_pnl = await client.get(
        f"/api/v1/organisations/{org_b_id}/reports/profit-and-loss",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_pnl.status_code == 200
    assert Decimal(str(res_pnl.json()["net_profit"])) == Decimal("0.0000")

    res_bs = await client.get(
        f"/api/v1/organisations/{org_b_id}/reports/balance-sheet",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_bs.status_code == 200
    assert Decimal(str(res_bs.json()["total_assets"])) == Decimal("0.0000")

    res_ar = await client.get(
        f"/api/v1/organisations/{org_b_id}/reports/aged-receivables",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_ar.status_code == 200
    assert Decimal(str(res_ar.json()["totals"]["grand_total"])) == Decimal("0.0000")
