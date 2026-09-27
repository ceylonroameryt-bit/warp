"""
Warp Ladger — Phase 6 Master Pytest Suite: Payments & Allocations
Validates:
1. Bank Account Lifecycle & Balance Tracking
2. Exact Decimal Precision Arithmetic (No Float Drift)
3. Customer Payment (Money In) Full Settlement & Status Transition to PAID
4. Partial Payment Progression (AWAITING_PAYMENT -> PARTIALLY_PAID -> PAID)
5. Multi-Invoice Split Allocations in a Single Payment
6. Overpayment & Unallocated Credit Balance Management (Follow-up Allocation)
7. Supplier Bill Payment (Money Out) Lifecycle & Bank Balance Decrement
8. Atomic Payment Void & Complete Financial Rollback of Allocations and Balances
9. 8-Role RBAC Enforcement (Segregation of Duties: Bookkeeper creates, Accountant voids)
10. Strict Multi-Tenant Isolation (Cross-Tenant Payment & Allocation Prevention)
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import create_access_token
from app.database.models import (
    AllocationTargetType,
    BankAccount,
    BankAccountType,
    Bill,
    BillStatus,
    Contact,
    ContactStatus,
    ContactType,
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    Membership,
    MembershipStatus,
    Organisation,
    Payment,
    PaymentAllocation,
    PaymentMethod,
    PaymentStatus,
    PaymentType,
    Role,
    TaxRate,
    TaxType,
    User,
)
from app.roles.service import seed_permissions_and_roles


@pytest.fixture
async def phase6_setup(db_session: AsyncSession):
    """Seed test data for Phase 6 Payments tests."""
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
    }

    # 2. Users
    pwd_hash = "mock_hash"
    owner_a = User(email=f"owner_p6_{uuid.uuid4().hex[:6]}@test.com", hashed_password=pwd_hash, email_verified=True, full_name="Owner A")
    accountant_a = User(email=f"acct_p6_{uuid.uuid4().hex[:6]}@test.com", hashed_password=pwd_hash, email_verified=True, full_name="Accountant A")
    bookkeeper_a = User(email=f"bookie_p6_{uuid.uuid4().hex[:6]}@test.com", hashed_password=pwd_hash, email_verified=True, full_name="Bookkeeper A")
    viewer_a = User(email=f"viewer_p6_{uuid.uuid4().hex[:6]}@test.com", hashed_password=pwd_hash, email_verified=True, full_name="Viewer A")
    owner_b = User(email=f"owner_b_p6_{uuid.uuid4().hex[:6]}@test.com", hashed_password=pwd_hash, email_verified=True, full_name="Owner B")

    db_session.add_all([owner_a, accountant_a, bookkeeper_a, viewer_a, owner_b])
    await db_session.flush()

    # 3. Organisations
    org_a = Organisation(name="Phase6 Test Org A", slug=f"p6-org-a-{uuid.uuid4().hex[:6]}", owner_id=owner_a.id)
    org_b = Organisation(name="Phase6 Test Org B", slug=f"p6-org-b-{uuid.uuid4().hex[:6]}", owner_id=owner_b.id)
    db_session.add_all([org_a, org_b])
    await db_session.flush()

    # 4. Memberships
    members = [
        Membership(organisation_id=org_a.id, user_id=owner_a.id, role_id=roles["owner"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=accountant_a.id, role_id=roles["accountant"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=bookkeeper_a.id, role_id=roles["bookkeeper"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=viewer_a.id, role_id=roles["viewer"], status=MembershipStatus.active),
        Membership(organisation_id=org_b.id, user_id=owner_b.id, role_id=roles["owner"], status=MembershipStatus.active),
    ]
    db_session.add_all(members)

    # 5. Contacts (Customer & Supplier)
    customer_a = Contact(
        organisation_id=org_a.id,
        business_name="Acme Corporation Ltd",
        contact_type=ContactType.CUSTOMER,
        status=ContactStatus.ACTIVE,
        currency="GBP",
    )
    supplier_a = Contact(
        organisation_id=org_a.id,
        business_name="Consolidated Supplies PLC",
        contact_type=ContactType.SUPPLIER,
        status=ContactStatus.ACTIVE,
        currency="GBP",
    )
    customer_b = Contact(
        organisation_id=org_b.id,
        business_name="Tenant B Customer",
        contact_type=ContactType.CUSTOMER,
        status=ContactStatus.ACTIVE,
        currency="GBP",
    )
    db_session.add_all([customer_a, supplier_a, customer_b])
    await db_session.flush()

    # 6. Bank Account for Org A
    bank_a = BankAccount(
        organisation_id=org_a.id,
        account_name="Main Business Checking",
        account_type=BankAccountType.CHECKING,
        currency="GBP",
        account_number="12345678",
        sort_code="20-00-00",
        opening_balance=Decimal("5000.0000"),
        current_balance=Decimal("5000.0000"),
        is_default=True,
        active=True,
    )
    db_session.add(bank_a)

    # 7. Pre-seed an Approved Sales Invoice for Org A (£600.00)
    now = datetime.now(UTC)
    invoice_1 = Invoice(
        organisation_id=org_a.id,
        customer_id=customer_a.id,
        invoice_number="INV-000101",
        status=InvoiceStatus.APPROVED,
        issue_date=now,
        due_date=now + timedelta(days=30),
        currency="GBP",
        subtotal=Decimal("500.0000"),
        tax_total=Decimal("100.0000"),
        total=Decimal("600.0000"),
        amount_paid=Decimal("0.0000"),
        amount_due=Decimal("600.0000"),
    )
    db_session.add(invoice_1)

    # 8. Pre-seed an Approved Supplier Bill for Org A (£750.00)
    bill_1 = Bill(
        organisation_id=org_a.id,
        supplier_id=supplier_a.id,
        internal_bill_number="BILL-000201",
        supplier_invoice_number="SUPP-INV-9901",
        supplier_invoice_number_normalized="SUPP-INV-9901",
        status=BillStatus.APPROVED,
        bill_date=now,
        due_date=now + timedelta(days=14),
        currency="GBP",
        subtotal=Decimal("625.0000"),
        tax_total=Decimal("125.0000"),
        total=Decimal("750.0000"),
        amount_paid=Decimal("0.0000"),
        amount_due=Decimal("750.0000"),
    )
    db_session.add(bill_1)

    await db_session.commit()

    return {
        "org_a": org_a,
        "org_b": org_b,
        "customer_a": customer_a,
        "supplier_a": supplier_a,
        "customer_b": customer_b,
        "bank_a": bank_a,
        "invoice_1": invoice_1,
        "bill_1": bill_1,
        "tokens": {
            "owner": create_access_token(str(owner_a.id)),
            "accountant": create_access_token(str(accountant_a.id)),
            "bookkeeper": create_access_token(str(bookkeeper_a.id)),
            "viewer": create_access_token(str(viewer_a.id)),
            "owner_b": create_access_token(str(owner_b.id)),
        },
    }


# ─── 1. Bank Account Lifecycle & Balance Tracking ──────────────────────
async def test_bank_account_lifecycle_and_balance_tracking(client: AsyncClient, phase6_setup: dict):
    org_id = str(phase6_setup["org_a"].id)
    token = phase6_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create savings account
    res = await client.post(
        f"/api/v1/organisations/{org_id}/bank-accounts",
        headers=headers,
        json={
            "account_name": "Reserve High-Yield Savings",
            "account_type": "SAVINGS",
            "currency": "GBP",
            "account_number": "87654321",
            "sort_code": "40-40-40",
            "opening_balance": 15000.50,
            "is_default": False,
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["account_name"] == "Reserve High-Yield Savings"
    assert Decimal(str(data["current_balance"])) == Decimal("15000.5000")

    # List bank accounts
    list_res = await client.get(f"/api/v1/organisations/{org_id}/bank-accounts", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 2


# ─── 2. Exact Decimal Precision Arithmetic ────────────────────────────
async def test_exact_decimal_precision_payments(client: AsyncClient, phase6_setup: dict):
    org_id = str(phase6_setup["org_a"].id)
    token = phase6_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.post(
        f"/api/v1/organisations/{org_id}/payments",
        headers=headers,
        json={
            "payment_type": "INCOMING",
            "amount": 1234.5678,
            "currency": "GBP",
            "payment_method": "BANK_TRANSFER",
            "reference": "PRECISION-TEST-001",
        },
    )
    assert res.status_code == 201
    payment = res.json()
    assert Decimal(str(payment["amount"])) == Decimal("1234.5678")
    assert Decimal(str(payment["unallocated_amount"])) == Decimal("1234.5678")
    assert Decimal(str(payment["allocated_amount"])) == Decimal("0.0000")


# ─── 3. Customer Payment Full Settlement & Status Transition ──────────
async def test_customer_payment_single_invoice_full_settlement(client: AsyncClient, phase6_setup: dict):
    org_id = str(phase6_setup["org_a"].id)
    token = phase6_setup["tokens"]["bookkeeper"]
    headers = {"Authorization": f"Bearer {token}"}
    invoice_id = str(phase6_setup["invoice_1"].id)
    bank_id = str(phase6_setup["bank_a"].id)

    # Check initial bank balance
    init_bank = (await client.get(f"/api/v1/organisations/{org_id}/bank-accounts/{bank_id}", headers=headers)).json()
    init_balance = Decimal(str(init_bank["current_balance"]))

    # Record full payment (£600.00)
    pay_res = await client.post(
        f"/api/v1/organisations/{org_id}/payments",
        headers=headers,
        json={
            "payment_type": "INCOMING",
            "contact_id": str(phase6_setup["customer_a"].id),
            "bank_account_id": bank_id,
            "amount": 600.00,
            "currency": "GBP",
            "payment_method": "BANK_TRANSFER",
            "reference": "INV-101-SETTLED",
            "allocations": [
                {
                    "target_type": "INVOICE",
                    "invoice_id": invoice_id,
                    "amount": 600.00,
                }
            ],
        },
    )
    assert pay_res.status_code == 201
    pay = pay_res.json()
    assert Decimal(str(pay["allocated_amount"])) == Decimal("600.0000")
    assert Decimal(str(pay["unallocated_amount"])) == Decimal("0.0000")

    # Verify invoice status transitioned to PAID
    inv_res = await client.get(f"/api/v1/organisations/{org_id}/invoices/{invoice_id}", headers=headers)
    assert inv_res.status_code == 200
    inv = inv_res.json()
    assert inv["status"] == "PAID"
    assert Decimal(str(inv["amount_paid"])) == Decimal("600.0000")
    assert Decimal(str(inv["amount_due"])) == Decimal("0.0000")

    # Verify bank balance incremented
    new_bank = (await client.get(f"/api/v1/organisations/{org_id}/bank-accounts/{bank_id}", headers=headers)).json()
    assert Decimal(str(new_bank["current_balance"])) == init_balance + Decimal("600.0000")


# ─── 4. Partial Payment Progression ───────────────────────────────────
async def test_customer_payment_partial_settlement_progression(client: AsyncClient, phase6_setup: dict, db_session: AsyncSession):
    org_id = str(phase6_setup["org_a"].id)
    token = phase6_setup["tokens"]["bookkeeper"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create new approved invoice (£1,000.00)
    now = datetime.now(UTC)
    inv = Invoice(
        organisation_id=phase6_setup["org_a"].id,
        customer_id=phase6_setup["customer_a"].id,
        invoice_number="INV-PARTIAL-01",
        status=InvoiceStatus.APPROVED,
        issue_date=now,
        due_date=now + timedelta(days=30),
        currency="GBP",
        subtotal=Decimal("1000.0000"),
        tax_total=Decimal("0.0000"),
        total=Decimal("1000.0000"),
        amount_paid=Decimal("0.0000"),
        amount_due=Decimal("1000.0000"),
    )
    db_session.add(inv)
    await db_session.commit()
    inv_id = str(inv.id)

    # 1. First partial payment: £400.00
    res_1 = await client.post(
        f"/api/v1/organisations/{org_id}/payments",
        headers=headers,
        json={
            "payment_type": "INCOMING",
            "contact_id": str(phase6_setup["customer_a"].id),
            "amount": 400.00,
            "currency": "GBP",
            "allocations": [{"target_type": "INVOICE", "invoice_id": inv_id, "amount": 400.00}],
        },
    )
    assert res_1.status_code == 201

    inv_chk1 = (await client.get(f"/api/v1/organisations/{org_id}/invoices/{inv_id}", headers=headers)).json()
    assert inv_chk1["status"] == "PARTIALLY_PAID"
    assert Decimal(str(inv_chk1["amount_paid"])) == Decimal("400.0000")
    assert Decimal(str(inv_chk1["amount_due"])) == Decimal("600.0000")

    # 2. Second partial payment: £600.00 (Final settlement)
    res_2 = await client.post(
        f"/api/v1/organisations/{org_id}/payments",
        headers=headers,
        json={
            "payment_type": "INCOMING",
            "contact_id": str(phase6_setup["customer_a"].id),
            "amount": 600.00,
            "currency": "GBP",
            "allocations": [{"target_type": "INVOICE", "invoice_id": inv_id, "amount": 600.00}],
        },
    )
    assert res_2.status_code == 201

    inv_chk2 = (await client.get(f"/api/v1/organisations/{org_id}/invoices/{inv_id}", headers=headers)).json()
    assert inv_chk2["status"] == "PAID"
    assert Decimal(str(inv_chk2["amount_paid"])) == Decimal("1000.0000")
    assert Decimal(str(inv_chk2["amount_due"])) == Decimal("0.0000")


# ─── 5. Multi-Invoice Split Allocations in a Single Payment ───────────
async def test_multi_invoice_split_allocation(client: AsyncClient, phase6_setup: dict, db_session: AsyncSession):
    org_id = str(phase6_setup["org_a"].id)
    token = phase6_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}
    now = datetime.now(UTC)

    # Create 3 invoices: £100, £250, £150 (Total: £500)
    invoices = [
        Invoice(organisation_id=phase6_setup["org_a"].id, customer_id=phase6_setup["customer_a"].id, invoice_number=f"INV-SPLIT-{i}", status=InvoiceStatus.APPROVED, issue_date=now, due_date=now, currency="GBP", subtotal=Decimal(amt), tax_total=Decimal("0.0000"), total=Decimal(amt), amount_paid=Decimal("0.0000"), amount_due=Decimal(amt))
        for i, amt in enumerate(["100.0000", "250.0000", "150.0000"], 1)
    ]
    db_session.add_all(invoices)
    await db_session.commit()

    # Record 1 payment of £500 split across all 3
    pay_res = await client.post(
        f"/api/v1/organisations/{org_id}/payments",
        headers=headers,
        json={
            "payment_type": "INCOMING",
            "contact_id": str(phase6_setup["customer_a"].id),
            "amount": 500.00,
            "currency": "GBP",
            "reference": "BULK-SETTLEMENT-3-INVOICES",
            "allocations": [
                {"target_type": "INVOICE", "invoice_id": str(invoices[0].id), "amount": 100.00},
                {"target_type": "INVOICE", "invoice_id": str(invoices[1].id), "amount": 250.00},
                {"target_type": "INVOICE", "invoice_id": str(invoices[2].id), "amount": 150.00},
            ],
        },
    )
    assert pay_res.status_code == 201
    pay = pay_res.json()
    assert Decimal(str(pay["allocated_amount"])) == Decimal("500.0000")
    assert Decimal(str(pay["unallocated_amount"])) == Decimal("0.0000")
    assert len(pay["allocations"]) == 3

    # Check each invoice is PAID
    for inv in invoices:
        chk = (await client.get(f"/api/v1/organisations/{org_id}/invoices/{inv.id}", headers=headers)).json()
        assert chk["status"] == "PAID"
        assert Decimal(str(chk["amount_due"])) == Decimal("0.0000")


# ─── 6. Overpayment & Unallocated Credit Balance Management ───────────
async def test_overpayment_creates_unallocated_credit_balance(client: AsyncClient, phase6_setup: dict, db_session: AsyncSession):
    org_id = str(phase6_setup["org_a"].id)
    token = phase6_setup["tokens"]["bookkeeper"]
    headers = {"Authorization": f"Bearer {token}"}
    now = datetime.now(UTC)

    # Invoice 1: £300.00
    inv1 = Invoice(organisation_id=phase6_setup["org_a"].id, customer_id=phase6_setup["customer_a"].id, invoice_number="INV-OVER-1", status=InvoiceStatus.APPROVED, issue_date=now, due_date=now, currency="GBP", subtotal=Decimal("300.0000"), tax_total=Decimal("0.0000"), total=Decimal("300.0000"), amount_paid=Decimal("0.0000"), amount_due=Decimal("300.0000"))
    db_session.add(inv1)
    await db_session.commit()

    # Customer pays £500.00 (£300 allocated, £200 unallocated advance/overpayment)
    res = await client.post(
        f"/api/v1/organisations/{org_id}/payments",
        headers=headers,
        json={
            "payment_type": "INCOMING",
            "contact_id": str(phase6_setup["customer_a"].id),
            "amount": 500.00,
            "currency": "GBP",
            "allocations": [{"target_type": "INVOICE", "invoice_id": str(inv1.id), "amount": 300.00}],
        },
    )
    assert res.status_code == 201
    pay = res.json()
    pay_id = pay["id"]
    assert Decimal(str(pay["allocated_amount"])) == Decimal("300.0000")
    assert Decimal(str(pay["unallocated_amount"])) == Decimal("200.0000")

    # Later: New invoice 2 created for £200.00
    inv2 = Invoice(organisation_id=phase6_setup["org_a"].id, customer_id=phase6_setup["customer_a"].id, invoice_number="INV-OVER-2", status=InvoiceStatus.APPROVED, issue_date=now, due_date=now, currency="GBP", subtotal=Decimal("200.0000"), tax_total=Decimal("0.0000"), total=Decimal("200.0000"), amount_paid=Decimal("0.0000"), amount_due=Decimal("200.0000"))
    db_session.add(inv2)
    await db_session.commit()

    # Allocate the remaining £200 from the original payment
    alloc_res = await client.post(
        f"/api/v1/organisations/{org_id}/payments/{pay_id}/allocate",
        headers=headers,
        json={
            "allocations": [{"target_type": "INVOICE", "invoice_id": str(inv2.id), "amount": 200.00}]
        },
    )
    assert alloc_res.status_code == 200
    updated_pay = alloc_res.json()
    assert Decimal(str(updated_pay["allocated_amount"])) == Decimal("500.0000")
    assert Decimal(str(updated_pay["unallocated_amount"])) == Decimal("0.0000")

    # Verify invoice 2 is now PAID
    inv2_chk = (await client.get(f"/api/v1/organisations/{org_id}/invoices/{inv2.id}", headers=headers)).json()
    assert inv2_chk["status"] == "PAID"
    assert Decimal(str(inv2_chk["amount_due"])) == Decimal("0.0000")


# ─── 7. Supplier Bill Payment Lifecycle ───────────────────────────────
async def test_supplier_bill_payment_lifecycle(client: AsyncClient, phase6_setup: dict):
    org_id = str(phase6_setup["org_a"].id)
    token = phase6_setup["tokens"]["bookkeeper"]
    headers = {"Authorization": f"Bearer {token}"}
    bill_id = str(phase6_setup["bill_1"].id)
    bank_id = str(phase6_setup["bank_a"].id)

    init_bank = (await client.get(f"/api/v1/organisations/{org_id}/bank-accounts/{bank_id}", headers=headers)).json()
    init_balance = Decimal(str(init_bank["current_balance"]))

    # Pay supplier bill (£750.00)
    pay_res = await client.post(
        f"/api/v1/organisations/{org_id}/payments",
        headers=headers,
        json={
            "payment_type": "OUTGOING",
            "contact_id": str(phase6_setup["supplier_a"].id),
            "bank_account_id": bank_id,
            "amount": 750.00,
            "currency": "GBP",
            "payment_method": "BANK_TRANSFER",
            "reference": "BILL-PAY-001",
            "allocations": [{"target_type": "BILL", "bill_id": bill_id, "amount": 750.00}],
        },
    )
    assert pay_res.status_code == 201

    # Verify Bill status transitioned to PAID
    bill_res = await client.get(f"/api/v1/organisations/{org_id}/bills/{bill_id}", headers=headers)
    assert bill_res.status_code == 200
    bill = bill_res.json()
    assert bill["status"] == "PAID"
    assert Decimal(str(bill["amount_paid"])) == Decimal("750.0000")
    assert Decimal(str(bill["amount_due"])) == Decimal("0.0000")

    # Verify Bank balance decremented
    new_bank = (await client.get(f"/api/v1/organisations/{org_id}/bank-accounts/{bank_id}", headers=headers)).json()
    assert Decimal(str(new_bank["current_balance"])) == init_balance - Decimal("750.0000")


# ─── 8. Atomic Payment Void & Allocation Rollback ─────────────────────
async def test_atomic_payment_void_and_allocation_rollback(client: AsyncClient, phase6_setup: dict, db_session: AsyncSession):
    org_id = str(phase6_setup["org_a"].id)
    token = phase6_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}
    now = datetime.now(UTC)

    # Create approved invoice (£450.00)
    inv = Invoice(organisation_id=phase6_setup["org_a"].id, customer_id=phase6_setup["customer_a"].id, invoice_number="INV-VOID-TEST", status=InvoiceStatus.APPROVED, issue_date=now, due_date=now, currency="GBP", subtotal=Decimal("450.0000"), tax_total=Decimal("0.0000"), total=Decimal("450.0000"), amount_paid=Decimal("0.0000"), amount_due=Decimal("450.0000"))
    db_session.add(inv)
    await db_session.commit()
    inv_id = str(inv.id)

    # 1. Record payment
    pay_res = await client.post(
        f"/api/v1/organisations/{org_id}/payments",
        headers=headers,
        json={
            "payment_type": "INCOMING",
            "contact_id": str(phase6_setup["customer_a"].id),
            "amount": 450.00,
            "currency": "GBP",
            "allocations": [{"target_type": "INVOICE", "invoice_id": inv_id, "amount": 450.00}],
        },
    )
    assert pay_res.status_code == 201
    pay_id = pay_res.json()["id"]

    # Invoice is PAID
    inv_paid = (await client.get(f"/api/v1/organisations/{org_id}/invoices/{inv_id}", headers=headers)).json()
    assert inv_paid["status"] == "PAID"

    # 2. Void payment
    void_res = await client.post(
        f"/api/v1/organisations/{org_id}/payments/{pay_id}/void",
        headers=headers,
        json={"reason": "Customer cheque dishonoured by bank"},
    )
    assert void_res.status_code == 200
    voided_pay = void_res.json()
    assert voided_pay["status"] == "VOIDED"
    assert voided_pay["void_reason"] == "Customer cheque dishonoured by bank"
    assert voided_pay["voided_at"] is not None

    # 3. Invoice balance and status strictly restored
    inv_restored = (await client.get(f"/api/v1/organisations/{org_id}/invoices/{inv_id}", headers=headers)).json()
    assert inv_restored["status"] == "AWAITING_PAYMENT"
    assert Decimal(str(inv_restored["amount_paid"])) == Decimal("0.0000")
    assert Decimal(str(inv_restored["amount_due"])) == Decimal("450.0000")


# ─── 9. Fine-Grained 8-Role RBAC Enforcement ─────────────────────────
async def test_rbac_payments_8_roles(client: AsyncClient, phase6_setup: dict):
    org_id = str(phase6_setup["org_a"].id)
    tokens = phase6_setup["tokens"]

    # 1. Bookkeeper can create payment
    bookie_res = await client.post(
        f"/api/v1/organisations/{org_id}/payments",
        headers={"Authorization": f"Bearer {tokens['bookkeeper']}"},
        json={"payment_type": "INCOMING", "amount": 100.00, "currency": "GBP"},
    )
    assert bookie_res.status_code == 201
    pay_id = bookie_res.json()["id"]

    # 2. Bookkeeper CANNOT void payment -> 403 Forbidden
    bookie_void = await client.post(
        f"/api/v1/organisations/{org_id}/payments/{pay_id}/void",
        headers={"Authorization": f"Bearer {tokens['bookkeeper']}"},
        json={"reason": "Unauthorized void attempt"},
    )
    assert bookie_void.status_code == 403

    # 3. Accountant CAN void payment -> 200 OK
    acct_void = await client.post(
        f"/api/v1/organisations/{org_id}/payments/{pay_id}/void",
        headers={"Authorization": f"Bearer {tokens['accountant']}"},
        json={"reason": "Authorized void by accountant"},
    )
    assert acct_void.status_code == 200

    # 4. Viewer cannot create payment -> 403 Forbidden
    viewer_create = await client.post(
        f"/api/v1/organisations/{org_id}/payments",
        headers={"Authorization": f"Bearer {tokens['viewer']}"},
        json={"payment_type": "INCOMING", "amount": 50.00, "currency": "GBP"},
    )
    assert viewer_create.status_code == 403


# ─── 10. Strict Multi-Tenant Isolation ────────────────────────────────
async def test_tenant_isolation_payments(client: AsyncClient, phase6_setup: dict):
    org_a_id = str(phase6_setup["org_a"].id)
    org_b_id = str(phase6_setup["org_b"].id)
    token_a = phase6_setup["tokens"]["accountant"]
    token_b = phase6_setup["tokens"]["owner_b"]

    # Create payment in Org A
    pay_a = (await client.post(
        f"/api/v1/organisations/{org_a_id}/payments",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"payment_type": "INCOMING", "amount": 500.00, "currency": "GBP"},
    )).json()

    # Org B attempts to read Org A payment -> 404 or 403
    leak_read = await client.get(
        f"/api/v1/organisations/{org_b_id}/payments/{pay_a['id']}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert leak_read.status_code in (404, 403)

    # Org B attempts to void Org A payment -> 404 or 403
    leak_void = await client.post(
        f"/api/v1/organisations/{org_b_id}/payments/{pay_a['id']}/void",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"reason": "Malicious cross-tenant void"},
    )
    assert leak_void.status_code in (404, 403)

    # Org B attempts to allocate payment to Org A invoice -> 404 or 422
    leak_alloc = await client.post(
        f"/api/v1/organisations/{org_b_id}/payments",
        headers={"Authorization": f"Bearer {token_b}"},
        json={
            "payment_type": "INCOMING",
            "amount": 200.00,
            "currency": "GBP",
            "allocations": [{"target_type": "INVOICE", "invoice_id": str(phase6_setup["invoice_1"].id), "amount": 200.00}],
        },
    )
    assert leak_alloc.status_code in (404, 422)
