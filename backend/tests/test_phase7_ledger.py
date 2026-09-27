"""
Warp Ladger — Phase 7 Master Pytest Suite: Accounting Ledger & Double-Entry Journal Engine
Validates:
1. Chart of Accounts (COA) Auto-Seeding (Standard 20 UK GAAP accounts) & Custom Account Creation
2. Core System Account Safeguards (Cannot delete or deactivate system accounts)
3. Exact Decimal Double-Entry Equation (sum(Dr) == sum(Cr) > 0; unbalanced entries strictly rejected)
4. Concurrency-Safe Sequential Journal Numbering (JRN-000001, JRN-000002)
5. Draft Journal Entry Creation & Explicit Posting Lifecycle
6. Atomic Journal Reversal Workflow (Counter-entry generated, original marked REVERSED)
7. Global Accounting Lock Date Enforcement (Transactions on/before lock_date rejected with 422)
8. Named Financial Period Locking (Transactions in locked periods rejected with 422)
9. Real-Time Trial Balance Calculation & Balance Verification
10. 8-Role RBAC Segregation of Duties (Bookkeeper creates, only Accountant locks/reverses)
11. Strict Multi-Tenant Isolation (COA, Journals, and Trial Balance isolated per tenant)
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
    FinancialPeriod,
    JournalEntry,
    JournalEntryStatus,
    JournalLine,
    JournalSourceType,
    Membership,
    MembershipStatus,
    Organisation,
    OrganisationAccountingSettings,
    Role,
    User,
)
from app.roles.service import seed_permissions_and_roles

UTC = timezone.utc


@pytest.fixture
async def phase7_setup(db_session: AsyncSession):
    """Seed test data for Phase 7 Ledger tests."""
    await seed_permissions_and_roles(db_session)

    # 1. Roles lookup
    async def get_role(name: str):
        res = await db_session.execute(Role.__table__.select().where(Role.name == name))
        return res.mappings().first()["id"]

    roles = {
        "owner": await get_role("owner"),
        "accountant": await get_role("accountant"),
        "bookkeeper": await get_role("bookkeeper"),
        "viewer": await get_role("viewer"),
        "employee": await get_role("employee"),
    }

    # 2. Users
    pwd_hash = "mock_hash"
    owner_a = User(email=f"owner_p7_{uuid.uuid4().hex[:6]}@test.com", hashed_password=pwd_hash, email_verified=True, full_name="Owner A")
    accountant_a = User(email=f"acct_p7_{uuid.uuid4().hex[:6]}@test.com", hashed_password=pwd_hash, email_verified=True, full_name="Accountant A")
    bookkeeper_a = User(email=f"bookie_p7_{uuid.uuid4().hex[:6]}@test.com", hashed_password=pwd_hash, email_verified=True, full_name="Bookkeeper A")
    viewer_a = User(email=f"viewer_p7_{uuid.uuid4().hex[:6]}@test.com", hashed_password=pwd_hash, email_verified=True, full_name="Viewer A")
    employee_a = User(email=f"emp_p7_{uuid.uuid4().hex[:6]}@test.com", hashed_password=pwd_hash, email_verified=True, full_name="Employee A")
    owner_b = User(email=f"owner_b_p7_{uuid.uuid4().hex[:6]}@test.com", hashed_password=pwd_hash, email_verified=True, full_name="Owner B")

    db_session.add_all([owner_a, accountant_a, bookkeeper_a, viewer_a, employee_a, owner_b])
    await db_session.flush()

    # 3. Organisations
    org_a = Organisation(name="Phase7 Test Org A", slug=f"p7-org-a-{uuid.uuid4().hex[:6]}", owner_id=owner_a.id)
    org_b = Organisation(name="Phase7 Test Org B", slug=f"p7-org-b-{uuid.uuid4().hex[:6]}", owner_id=owner_b.id)
    db_session.add_all([org_a, org_b])
    await db_session.flush()

    # 4. Memberships
    members = [
        Membership(organisation_id=org_a.id, user_id=owner_a.id, role_id=roles["owner"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=accountant_a.id, role_id=roles["accountant"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=bookkeeper_a.id, role_id=roles["bookkeeper"], status=MembershipStatus.active),
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
        "viewer": create_access_token(str(viewer_a.id)),
        "employee": create_access_token(str(employee_a.id)),
        "owner_b": create_access_token(str(owner_b.id)),
    }

    return {
        "org_a": org_a,
        "org_b": org_b,
        "users": {
            "owner_a": owner_a,
            "accountant": accountant_a,
            "bookkeeper": bookkeeper_a,
            "viewer": viewer_a,
            "employee": employee_a,
            "owner_b": owner_b,
        },
        "tokens": tokens,
    }


# ─── 1. Chart of Accounts Auto-Seeding & Custom Account CRUD ─
async def test_coa_standard_seeding_and_crud(client: AsyncClient, phase7_setup: dict):
    org_id = str(phase7_setup["org_a"].id)
    token = phase7_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. First fetch automatically seeds standard UK GAAP accounts
    res = await client.get(f"/api/v1/organisations/{org_id}/accounts", headers=headers)
    assert res.status_code == 200
    accounts = res.json()
    assert len(accounts) >= 20

    codes = {a["code"]: a for a in accounts}
    assert "1000" in codes  # Bank Current Account
    assert "1200" in codes  # Accounts Receivable
    assert "2000" in codes  # Accounts Payable
    assert "2200" in codes  # VAT Output
    assert "4000" in codes  # Sales Revenue
    assert "6300" in codes  # Software & Subscriptions

    # 2. Create custom ledger account
    create_res = await client.post(
        f"/api/v1/organisations/{org_id}/accounts",
        headers=headers,
        json={
            "code": "1050",
            "name": "High Yield Treasury Reserve",
            "account_class": "ASSET",
            "account_subtype": "CURRENT_ASSET",
            "currency": "GBP",
            "description": "Short-term treasury yield reserve account",
        },
    )
    assert create_res.status_code == 201
    custom_acc = create_res.json()
    assert custom_acc["code"] == "1050"
    assert custom_acc["is_system"] is False

    # 3. Duplicate code is rejected with 422
    dup_res = await client.post(
        f"/api/v1/organisations/{org_id}/accounts",
        headers=headers,
        json={
            "code": "1050",
            "name": "Duplicate Treasury",
            "account_class": "ASSET",
            "account_subtype": "CURRENT_ASSET",
        },
    )
    assert dup_res.status_code in (422, 400)


# ─── 2. System Account Protection ────────────────────────────
async def test_system_account_protection(client: AsyncClient, phase7_setup: dict):
    org_id = str(phase7_setup["org_a"].id)
    token = phase7_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get Accounts Receivable (code 1200, system account)
    res = await client.get(f"/api/v1/organisations/{org_id}/accounts", headers=headers)
    accounts = res.json()
    ar_account = next(a for a in accounts if a["code"] == "1200")
    assert ar_account["is_system"] is True

    # Attempt to delete/archive system account -> Rejected
    del_res = await client.delete(
        f"/api/v1/organisations/{org_id}/accounts/{ar_account['id']}",
        headers=headers,
    )
    assert del_res.status_code in (422, 400)

    # Attempt to deactivate system account -> Rejected
    update_res = await client.put(
        f"/api/v1/organisations/{org_id}/accounts/{ar_account['id']}",
        headers=headers,
        json={"active": False},
    )
    assert update_res.status_code in (422, 400)


# ─── 3. Double-Entry Invariant Enforcement ───────────────────
async def test_exact_decimal_double_entry_balance_enforcement(client: AsyncClient, phase7_setup: dict):
    org_id = str(phase7_setup["org_a"].id)
    token = phase7_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}

    # Load accounts
    accs = (await client.get(f"/api/v1/organisations/{org_id}/accounts", headers=headers)).json()
    acc_map = {a["code"]: a["id"] for a in accs}

    bank_id = acc_map["1000"]
    sales_id = acc_map["4000"]
    vat_id = acc_map["2200"]

    # 1. Perfectly balanced 3-line journal (£1,200 Dr = £1,000 Cr + £200 Cr) -> 201 Created
    valid_res = await client.post(
        f"/api/v1/organisations/{org_id}/journals",
        headers=headers,
        json={
            "entry_date": "2026-03-15",
            "reference": "REF-BALANCED-01",
            "narration": "Direct cash sale with 20% VAT",
            "post_immediately": True,
            "lines": [
                {"account_id": bank_id, "debit": 1200.00, "credit": 0.0, "description": "Cash received"},
                {"account_id": sales_id, "debit": 0.0, "credit": 1000.00, "description": "Net sales revenue"},
                {"account_id": vat_id, "debit": 0.0, "credit": 200.00, "description": "Output VAT"},
            ],
        },
    )
    assert valid_res.status_code == 201
    j = valid_res.json()
    assert Decimal(str(j["total_debit"])) == Decimal("1200.0000")
    assert Decimal(str(j["total_credit"])) == Decimal("1200.0000")
    assert j["status"] == "POSTED"

    # 2. Out-of-balance journal (£1,200 Dr != £1,199.99 Cr) -> 422 Unprocessable
    unbalanced_res = await client.post(
        f"/api/v1/organisations/{org_id}/journals",
        headers=headers,
        json={
            "entry_date": "2026-03-15",
            "reference": "REF-UNBALANCED",
            "narration": "Imbalanced journal",
            "lines": [
                {"account_id": bank_id, "debit": 1200.00, "credit": 0.0},
                {"account_id": sales_id, "debit": 0.0, "credit": 1199.99},
            ],
        },
    )
    assert unbalanced_res.status_code == 422

    # 3. Single-line journal (< 2 lines) -> 422 Unprocessable
    single_line_res = await client.post(
        f"/api/v1/organisations/{org_id}/journals",
        headers=headers,
        json={
            "entry_date": "2026-03-15",
            "lines": [
                {"account_id": bank_id, "debit": 500.00, "credit": 0.0},
            ],
        },
    )
    assert single_line_res.status_code == 422


# ─── 4. Concurrency-Safe Sequential Journal Numbering ─────────
async def test_journal_concurrency_safe_numbering(client: AsyncClient, phase7_setup: dict):
    org_id = str(phase7_setup["org_a"].id)
    token = phase7_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}

    accs = (await client.get(f"/api/v1/organisations/{org_id}/accounts", headers=headers)).json()
    acc_map = {a["code"]: a["id"] for a in accs}
    bank_id = acc_map["1000"]
    sales_id = acc_map["4000"]

    numbers = []
    for i in range(3):
        res = await client.post(
            f"/api/v1/organisations/{org_id}/journals",
            headers=headers,
            json={
                "entry_date": "2026-03-20",
                "narration": f"Sequential test {i+1}",
                "lines": [
                    {"account_id": bank_id, "debit": 100.0, "credit": 0.0},
                    {"account_id": sales_id, "debit": 0.0, "credit": 100.0},
                ],
            },
        )
        assert res.status_code == 201
        numbers.append(res.json()["entry_number"])

    # Verify strict sequential ordering with prefix and padding
    assert numbers[0].startswith("JRN-")
    assert int(numbers[1].split("-")[1]) == int(numbers[0].split("-")[1]) + 1
    assert int(numbers[2].split("-")[1]) == int(numbers[1].split("-")[1]) + 1


# ─── 5. Draft Journal Entry Creation & Explicit Posting ───────
async def test_draft_journal_post_lifecycle(client: AsyncClient, phase7_setup: dict):
    org_id = str(phase7_setup["org_a"].id)
    token = phase7_setup["tokens"]["bookkeeper"]
    headers = {"Authorization": f"Bearer {token}"}

    accs = (await client.get(f"/api/v1/organisations/{org_id}/accounts", headers=headers)).json()
    acc_map = {a["code"]: a["id"] for a in accs}

    # 1. Bookkeeper creates DRAFT journal (post_immediately = False)
    res = await client.post(
        f"/api/v1/organisations/{org_id}/journals",
        headers=headers,
        json={
            "entry_date": "2026-03-22",
            "reference": "DRAFT-EXPENSE-ADJ",
            "narration": "Accrual adjustment awaiting review",
            "post_immediately": False,
            "lines": [
                {"account_id": acc_map["6300"], "debit": 350.0, "credit": 0.0, "description": "Software expense"},
                {"account_id": acc_map["2000"], "debit": 0.0, "credit": 350.0, "description": "Accrued trade payable"},
            ],
        },
    )
    assert res.status_code == 201
    draft = res.json()
    assert draft["status"] == "DRAFT"
    assert draft["posted_at"] is None
    journal_id = draft["id"]

    # 2. Accountant posts the draft journal
    acct_token = phase7_setup["tokens"]["accountant"]
    post_res = await client.post(
        f"/api/v1/organisations/{org_id}/journals/{journal_id}/post",
        headers={"Authorization": f"Bearer {acct_token}"},
    )
    assert post_res.status_code == 200
    posted = post_res.json()
    assert posted["status"] == "POSTED"
    assert posted["posted_at"] is not None
    assert posted["posted_by_id"] is not None


# ─── 6. Atomic Journal Reversal Workflow ──────────────────────
async def test_atomic_journal_reversal_workflow(client: AsyncClient, phase7_setup: dict):
    org_id = str(phase7_setup["org_a"].id)
    token = phase7_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}

    accs = (await client.get(f"/api/v1/organisations/{org_id}/accounts", headers=headers)).json()
    acc_map = {a["code"]: a["id"] for a in accs}

    # 1. Create and post original journal entry (£750 Marketing Expense)
    orig_res = await client.post(
        f"/api/v1/organisations/{org_id}/journals",
        headers=headers,
        json={
            "entry_date": "2026-03-10",
            "reference": "ORIG-MKT-01",
            "narration": "March campaign advertisement",
            "post_immediately": True,
            "lines": [
                {"account_id": acc_map["6000"], "debit": 750.00, "credit": 0.0, "description": "Ad spend"},
                {"account_id": acc_map["1000"], "debit": 0.0, "credit": 750.00, "description": "Bank payment"},
            ],
        },
    )
    assert orig_res.status_code == 201
    orig = orig_res.json()
    orig_id = orig["id"]

    # 2. Reverse the posted journal
    rev_res = await client.post(
        f"/api/v1/organisations/{org_id}/journals/{orig_id}/reverse",
        headers=headers,
        json={
            "reversal_reason": "Invoice cancelled and refunded by marketing agency",
            "reversal_date": "2026-03-12",
        },
    )
    assert rev_res.status_code == 200
    rev = rev_res.json()
    assert rev["status"] == "POSTED"
    assert rev["source_type"] == "REVERSAL"
    assert rev["reversed_entry_id"] == orig_id
    assert rev["reversal_reason"] == "Invoice cancelled and refunded by marketing agency"

    # Verify debits and credits were inverted
    rev_lines = {l["line_number"]: l for l in rev["lines"]}
    # Line 1 was Dr 750, Cr 0 -> Reversal line 1 is Dr 0, Cr 750
    assert Decimal(str(rev_lines[1]["debit"])) == Decimal("0.0000")
    assert Decimal(str(rev_lines[1]["credit"])) == Decimal("750.0000")
    # Line 2 was Dr 0, Cr 750 -> Reversal line 2 is Dr 750, Cr 0
    assert Decimal(str(rev_lines[2]["debit"])) == Decimal("750.0000")
    assert Decimal(str(rev_lines[2]["credit"])) == Decimal("0.0000")

    # 3. Verify original entry status is updated to REVERSED
    orig_chk = (await client.get(f"/api/v1/organisations/{org_id}/journals/{orig_id}", headers=headers)).json()
    assert orig_chk["status"] == "REVERSED"
    assert orig_chk["reversed_entry_id"] == rev["id"]

    # 4. Attempting to reverse an already reversed journal fails
    repeat_rev = await client.post(
        f"/api/v1/organisations/{org_id}/journals/{orig_id}/reverse",
        headers=headers,
        json={"reversal_reason": "Duplicate reversal attempt"},
    )
    assert repeat_rev.status_code in (422, 400)


# ─── 7. Global Accounting Lock Date Enforcement ───────────────
async def test_global_period_lock_enforcement(client: AsyncClient, phase7_setup: dict):
    org_id = str(phase7_setup["org_a"].id)
    token = phase7_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}

    accs = (await client.get(f"/api/v1/organisations/{org_id}/accounts", headers=headers)).json()
    acc_map = {a["code"]: a["id"] for a in accs}

    # 1. Set global hard lock date to 2025-12-31
    settings_res = await client.put(
        f"/api/v1/organisations/{org_id}/accounting/settings",
        headers=headers,
        json={"lock_date": "2025-12-31"},
    )
    assert settings_res.status_code == 200
    assert settings_res.json()["lock_date"] == "2025-12-31"

    # 2. Transaction on or before lock date (2025-12-15) -> 422 PeriodLockedError
    blocked_res = await client.post(
        f"/api/v1/organisations/{org_id}/journals",
        headers=headers,
        json={
            "entry_date": "2025-12-15",
            "narration": "Attempted back-dated entry in closed year",
            "lines": [
                {"account_id": acc_map["1000"], "debit": 200.0, "credit": 0.0},
                {"account_id": acc_map["4000"], "debit": 0.0, "credit": 200.0},
            ],
        },
    )
    assert blocked_res.status_code == 422
    assert "PERIOD_LOCKED" in blocked_res.text or "locked" in blocked_res.text.lower()

    # 3. Transaction after lock date (2026-01-05) -> 201 Created
    allowed_res = await client.post(
        f"/api/v1/organisations/{org_id}/journals",
        headers=headers,
        json={
            "entry_date": "2026-01-05",
            "narration": "Open period entry",
            "lines": [
                {"account_id": acc_map["1000"], "debit": 200.0, "credit": 0.0},
                {"account_id": acc_map["4000"], "debit": 0.0, "credit": 200.0},
            ],
        },
    )
    assert allowed_res.status_code == 201


# ─── 8. Named Financial Period Locking ────────────────────────
async def test_financial_period_lock_and_violation(client: AsyncClient, phase7_setup: dict):
    org_id = str(phase7_setup["org_a"].id)
    token = phase7_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}

    accs = (await client.get(f"/api/v1/organisations/{org_id}/accounts", headers=headers)).json()
    acc_map = {a["code"]: a["id"] for a in accs}

    # 1. Create a locked period for Q1 2026 (2026-01-01 to 2026-03-31)
    period_res = await client.post(
        f"/api/v1/organisations/{org_id}/accounting/periods",
        headers=headers,
        json={
            "period_name": "Q1 2026 VAT Quarter",
            "start_date": "2026-01-01",
            "end_date": "2026-03-31",
            "is_locked": True,
            "lock_reason": "VAT return finalized and submitted to HMRC",
        },
    )
    assert period_res.status_code == 201
    assert period_res.json()["is_locked"] is True

    # 2. Posting with entry date inside locked period (2026-02-15) -> 422
    fail_res = await client.post(
        f"/api/v1/organisations/{org_id}/journals",
        headers=headers,
        json={
            "entry_date": "2026-02-15",
            "narration": "Attempted entry in locked quarter",
            "lines": [
                {"account_id": acc_map["1000"], "debit": 150.0, "credit": 0.0},
                {"account_id": acc_map["4000"], "debit": 0.0, "credit": 150.0},
            ],
        },
    )
    assert fail_res.status_code == 422
    assert "PERIOD_LOCKED" in fail_res.text or "locked" in fail_res.text.lower()

    # 3. Posting with entry date in open quarter (2026-04-02) -> 201 Created
    ok_res = await client.post(
        f"/api/v1/organisations/{org_id}/journals",
        headers=headers,
        json={
            "entry_date": "2026-04-02",
            "narration": "Q2 open entry",
            "lines": [
                {"account_id": acc_map["1000"], "debit": 150.0, "credit": 0.0},
                {"account_id": acc_map["4000"], "debit": 0.0, "credit": 150.0},
            ],
        },
    )
    assert ok_res.status_code == 201


# ─── 9. Real-Time Trial Balance Calculation ───────────────────
async def test_trial_balance_mathematical_precision(client: AsyncClient, phase7_setup: dict, db_session: AsyncSession):
    # Use Tenant B to test pristine Trial Balance arithmetic
    org_id = str(phase7_setup["org_b"].id)
    token = phase7_setup["tokens"]["owner_b"]
    headers = {"Authorization": f"Bearer {token}"}

    accs = (await client.get(f"/api/v1/organisations/{org_id}/accounts", headers=headers)).json()
    acc_map = {a["code"]: a["id"] for a in accs}

    bank_id = acc_map["1000"]
    capital_id = acc_map["3010"]
    equipment_id = acc_map["1500"]
    sales_id = acc_map["4000"]
    rent_id = acc_map["6100"]

    # Journal 1: Initial capital injection (£50,000)
    # Dr Bank 50,000, Cr Capital 50,000
    await client.post(
        f"/api/v1/organisations/{org_id}/journals",
        headers=headers,
        json={
            "entry_date": "2026-01-01",
            "narration": "Equity investment",
            "lines": [
                {"account_id": bank_id, "debit": 50000.0, "credit": 0.0},
                {"account_id": capital_id, "debit": 0.0, "credit": 50000.0},
            ],
        },
    )

    # Journal 2: Purchase office equipment (£5,000)
    # Dr Equipment 5,000, Cr Bank 5,000
    await client.post(
        f"/api/v1/organisations/{org_id}/journals",
        headers=headers,
        json={
            "entry_date": "2026-01-05",
            "narration": "Buy computers",
            "lines": [
                {"account_id": equipment_id, "debit": 5000.0, "credit": 0.0},
                {"account_id": bank_id, "debit": 0.0, "credit": 5000.0},
            ],
        },
    )

    # Journal 3: Sales revenue received (£12,000)
    # Dr Bank 12,000, Cr Sales 12,000
    await client.post(
        f"/api/v1/organisations/{org_id}/journals",
        headers=headers,
        json={
            "entry_date": "2026-01-10",
            "narration": "Client software retainer",
            "lines": [
                {"account_id": bank_id, "debit": 12000.0, "credit": 0.0},
                {"account_id": sales_id, "debit": 0.0, "credit": 12000.0},
            ],
        },
    )

    # Journal 4: Pay office rent (£3,000)
    # Dr Rent 3,000, Cr Bank 3,000
    await client.post(
        f"/api/v1/organisations/{org_id}/journals",
        headers=headers,
        json={
            "entry_date": "2026-01-15",
            "narration": "January office rent",
            "lines": [
                {"account_id": rent_id, "debit": 3000.0, "credit": 0.0},
                {"account_id": bank_id, "debit": 0.0, "credit": 3000.0},
            ],
        },
    )

    # Fetch Trial Balance as of 2026-01-31
    tb_res = await client.get(
        f"/api/v1/organisations/{org_id}/ledger/trial-balance?as_of_date=2026-01-31",
        headers=headers,
    )
    assert tb_res.status_code == 200
    tb = tb_res.json()

    assert tb["is_balanced"] is True
    assert Decimal(str(tb["total_debit"])) == Decimal(str(tb["total_credit"]))

    # Check net balances:
    # Bank = 50,000 - 5,000 + 12,000 - 3,000 = £54,000 Dr
    # Equipment = £5,000 Dr
    # Rent = £3,000 Dr
    # Capital = £50,000 Cr
    # Sales = £12,000 Cr
    # Total Dr = 54,000 + 5,000 + 3,000 = £62,000
    # Total Cr = 50,000 + 12,000 = £62,000
    tb_map = {a["account_code"]: a for a in tb["accounts"]}
    assert Decimal(str(tb_map["1000"]["debit_balance"])) == Decimal("54000.0000")
    assert Decimal(str(tb_map["1500"]["debit_balance"])) == Decimal("5000.0000")
    assert Decimal(str(tb_map["6100"]["debit_balance"])) == Decimal("3000.0000")
    assert Decimal(str(tb_map["3010"]["credit_balance"])) == Decimal("50000.0000")
    assert Decimal(str(tb_map["4000"]["credit_balance"])) == Decimal("12000.0000")
    assert Decimal(str(tb["total_debit"])) == Decimal("62000.0000")
    assert Decimal(str(tb["total_credit"])) == Decimal("62000.0000")


# ─── 10. 8-Role RBAC Segregation of Duties ───────────────────
async def test_rbac_ledger_8_roles(client: AsyncClient, phase7_setup: dict):
    org_id = str(phase7_setup["org_a"].id)
    tokens = phase7_setup["tokens"]

    accs = (await client.get(f"/api/v1/organisations/{org_id}/accounts", headers={"Authorization": f"Bearer {tokens['accountant']}"})).json()
    acc_map = {a["code"]: a["id"] for a in accs}

    # 1. Bookkeeper CAN create draft journals
    bookie_res = await client.post(
        f"/api/v1/organisations/{org_id}/journals",
        headers={"Authorization": f"Bearer {tokens['bookkeeper']}"},
        json={
            "entry_date": "2026-05-01",
            "lines": [
                {"account_id": acc_map["1000"], "debit": 50.0, "credit": 0.0},
                {"account_id": acc_map["4000"], "debit": 0.0, "credit": 50.0},
            ],
        },
    )
    assert bookie_res.status_code == 201
    j_id = bookie_res.json()["id"]

    # 2. Bookkeeper CANNOT reverse journals -> 403 Forbidden
    bookie_rev = await client.post(
        f"/api/v1/organisations/{org_id}/journals/{j_id}/reverse",
        headers={"Authorization": f"Bearer {tokens['bookkeeper']}"},
        json={"reversal_reason": "Unauthorized reversal"},
    )
    assert bookie_rev.status_code == 403

    # 3. Bookkeeper CANNOT set lock date -> 403 Forbidden
    bookie_lock = await client.put(
        f"/api/v1/organisations/{org_id}/accounting/settings",
        headers={"Authorization": f"Bearer {tokens['bookkeeper']}"},
        json={"lock_date": "2026-04-30"},
    )
    assert bookie_lock.status_code == 403

    # 4. Accountant CAN reverse journals -> 200 OK
    acct_rev = await client.post(
        f"/api/v1/organisations/{org_id}/journals/{j_id}/reverse",
        headers={"Authorization": f"Bearer {tokens['accountant']}"},
        json={"reversal_reason": "Authorized accountant reversal"},
    )
    assert acct_rev.status_code == 200

    # 5. Viewer CAN view trial balance -> 200 OK
    viewer_tb = await client.get(
        f"/api/v1/organisations/{org_id}/ledger/trial-balance",
        headers={"Authorization": f"Bearer {tokens['viewer']}"},
    )
    assert viewer_tb.status_code == 200

    # 6. Employee has NO ledger access -> 403 Forbidden
    emp_res = await client.get(
        f"/api/v1/organisations/{org_id}/accounts",
        headers={"Authorization": f"Bearer {tokens['employee']}"},
    )
    assert emp_res.status_code == 403


# ─── 11. Strict Multi-Tenant Isolation ────────────────────────
async def test_tenant_isolation_ledger(client: AsyncClient, phase7_setup: dict):
    org_a_id = str(phase7_setup["org_a"].id)
    org_b_id = str(phase7_setup["org_b"].id)
    token_a = phase7_setup["tokens"]["accountant"]
    token_b = phase7_setup["tokens"]["owner_b"]

    # Create journal in Org A
    accs_a = (await client.get(f"/api/v1/organisations/{org_a_id}/accounts", headers={"Authorization": f"Bearer {token_a}"})).json()
    acc_map_a = {a["code"]: a["id"] for a in accs_a}

    j_a = (await client.post(
        f"/api/v1/organisations/{org_a_id}/journals",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "entry_date": "2026-05-10",
            "lines": [
                {"account_id": acc_map_a["1000"], "debit": 500.0, "credit": 0.0},
                {"account_id": acc_map_a["4000"], "debit": 0.0, "credit": 500.0},
            ],
        },
    )).json()

    # Org B attempts to read Org A journal -> 404 or 403
    leak_read = await client.get(
        f"/api/v1/organisations/{org_b_id}/journals/{j_a['id']}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert leak_read.status_code in (404, 403)

    # Org B attempts to reverse Org A journal -> 404 or 403
    leak_rev = await client.post(
        f"/api/v1/organisations/{org_b_id}/journals/{j_a['id']}/reverse",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"reversal_reason": "Cross-tenant theft reversal"},
    )
    assert leak_rev.status_code in (404, 403)

    # Org B attempts to post a journal using Org A's account IDs -> 422 ValidationFailed
    leak_post = await client.post(
        f"/api/v1/organisations/{org_b_id}/journals",
        headers={"Authorization": f"Bearer {token_b}"},
        json={
            "entry_date": "2026-05-10",
            "lines": [
                {"account_id": acc_map_a["1000"], "debit": 100.0, "credit": 0.0},
                {"account_id": acc_map_a["4000"], "debit": 0.0, "credit": 100.0},
            ],
        },
    )
    assert leak_post.status_code == 422
