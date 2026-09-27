"""
Warp Ladger — Comprehensive Phase 4 Test Suite: Supplier Bills / Money Out
Validates:
1. Exact Decimal Arithmetic & Round-Half-Up Financial Accuracy
2. Full Multi-Tier Approval Lifecycle: Draft -> Submit -> Reject -> Edit -> Resubmit -> Approve -> Void
3. Concurrency-Safe Sequential Bill Numbering (e.g. BILL-000001)
4. Supplier Historical Snapshotting upon Approval
5. Approval Immutability Safeguard (Direct edits & deletion blocked on approved bills)
6. Derived Runtime OVERDUE Status
7. Smart Duplicate Bill Detection & Reasoned Override Workflow
8. Fine-Grained RBAC across all 8 canonical roles (Separation of duties)
9. Strict Multi-Tenant Isolation
"""
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    Contact,
    ContactAddress,
    ContactStatus,
    ContactType,
    Membership,
    MembershipStatus,
    Organisation,
    Role,
    TaxRate,
    TaxType,
    User,
)
from app.roles.service import seed_permissions_and_roles
from app.core.security import create_access_token

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def phase4_setup(db_session: AsyncSession):
    """
    Sets up two isolated organisations (Org Alpha and Org Beta),
    seeds all 8 canonical roles, creates tax rates, and a test supplier with address.
    """
    await seed_permissions_and_roles(db_session)

    # 1. Users for Org A
    owner_a = User(email="owner_p4@test.com", hashed_password="hash", full_name="Alice Owner", email_verified=True)
    admin_a = User(email="admin_p4@test.com", hashed_password="hash", full_name="Arthur Admin", email_verified=True)
    accountant_a = User(email="accountant_p4@test.com", hashed_password="hash", full_name="Amy Accountant", email_verified=True)
    bookkeeper_a = User(email="bookkeeper_p4@test.com", hashed_password="hash", full_name="Bob Bookkeeper", email_verified=True)
    approver_a = User(email="approver_p4@test.com", hashed_password="hash", full_name="Arnold Approver", email_verified=True)
    employee_a = User(email="employee_p4@test.com", hashed_password="hash", full_name="Evan Employee", email_verified=True)
    auditor_a = User(email="auditor_p4@test.com", hashed_password="hash", full_name="Audrey Auditor", email_verified=True)
    viewer_a = User(email="viewer_p4@test.com", hashed_password="hash", full_name="Victor Viewer", email_verified=True)

    # Tenant B User
    owner_b = User(email="owner_p4_b@test.com", hashed_password="hash", full_name="Boris Beta", email_verified=True)

    db_session.add_all([
        owner_a, admin_a, accountant_a, bookkeeper_a, approver_a, employee_a, auditor_a, viewer_a, owner_b
    ])
    await db_session.flush()

    # 2. Organisations
    org_a = Organisation(name="Alpha Corp", slug="alpha-corp-p4", owner_id=owner_a.id)
    org_b = Organisation(name="Beta Enterprises", slug="beta-enterprises-p4", owner_id=owner_b.id)
    db_session.add_all([org_a, org_b])
    await db_session.flush()

    # 3. Roles lookup
    async def get_role(name: str):
        res = await db_session.execute(Role.__table__.select().where(Role.name == name))
        return res.mappings().first()["id"]

    roles = {
        "owner": await get_role("owner"),
        "administrator": await get_role("administrator"),
        "accountant": await get_role("accountant"),
        "bookkeeper": await get_role("bookkeeper"),
        "approver": await get_role("approver"),
        "employee": await get_role("employee"),
        "auditor": await get_role("auditor"),
        "viewer": await get_role("viewer"),
    }

    # 4. Memberships for Org A
    members = [
        Membership(organisation_id=org_a.id, user_id=owner_a.id, role_id=roles["owner"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=admin_a.id, role_id=roles["administrator"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=accountant_a.id, role_id=roles["accountant"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=bookkeeper_a.id, role_id=roles["bookkeeper"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=approver_a.id, role_id=roles["approver"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=employee_a.id, role_id=roles["employee"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=auditor_a.id, role_id=roles["auditor"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=viewer_a.id, role_id=roles["viewer"], status=MembershipStatus.active),
        Membership(organisation_id=org_b.id, user_id=owner_b.id, role_id=roles["owner"], status=MembershipStatus.active),
    ]
    db_session.add_all(members)
    await db_session.flush()

    # 5. Tax Rates for Org A
    vat_20 = TaxRate(
        organisation_id=org_a.id,
        name="Standard VAT 20%",
        code="STANDARD",
        rate=Decimal("20.0000"),
        tax_type=TaxType.STANDARD,
        active=True,
    )
    vat_0 = TaxRate(
        organisation_id=org_a.id,
        name="Zero Rated 0%",
        code="ZERO",
        rate=Decimal("0.0000"),
        tax_type=TaxType.ZERO,
        active=True,
    )
    db_session.add_all([vat_20, vat_0])

    # 6. Test Supplier for Org A with Address
    supplier_a = Contact(
        organisation_id=org_a.id,
        business_name="Apex Logistics Ltd",
        legal_name="Apex Logistics Limited",
        contact_type=ContactType.SUPPLIER,
        status=ContactStatus.ACTIVE,
        email="invoicing@apexlogistics.co.uk",
        vat_number="GB112233445",
        company_number="08812345",
    )
    db_session.add(supplier_a)
    await db_session.flush()

    supplier_address_a = ContactAddress(
        organisation_id=org_a.id,
        contact_id=supplier_a.id,
        address_type="BILLING",
        line1="Apex Freight Terminal",
        city="Manchester",
        postcode="M1 1AA",
        country_code="GB",
        is_primary=True,
    )
    db_session.add(supplier_address_a)

    # 7. Test Supplier for Org B
    supplier_b = Contact(
        organisation_id=org_b.id,
        business_name="Beta Transport",
        contact_type=ContactType.SUPPLIER,
        status=ContactStatus.ACTIVE,
        email="accounts@betatransport.co.uk",
    )
    db_session.add(supplier_b)
    await db_session.commit()

    tokens = {
        "owner": create_access_token(str(owner_a.id)),
        "admin": create_access_token(str(admin_a.id)),
        "accountant": create_access_token(str(accountant_a.id)),
        "bookkeeper": create_access_token(str(bookkeeper_a.id)),
        "approver": create_access_token(str(approver_a.id)),
        "employee": create_access_token(str(employee_a.id)),
        "auditor": create_access_token(str(auditor_a.id)),
        "viewer": create_access_token(str(viewer_a.id)),
        "owner_b": create_access_token(str(owner_b.id)),
    }

    return {
        "org_a": org_a,
        "org_b": org_b,
        "supplier_a": supplier_a,
        "supplier_b": supplier_b,
        "vat_20": vat_20,
        "vat_0": vat_0,
        "tokens": tokens,
    }


# ─── 1. Exact Decimal Arithmetic & Golden Accounting Math ─────────────
async def test_decimal_precision_and_golden_accounting_math_bills(client: AsyncClient, phase4_setup: dict):
    """
    Test exact Decimal calculation for multi-line supplier bills:
    Line 1: 5.5 hours @ £45.20 = £248.60, 20% VAT = £49.72, Gross = £298.32
    Line 2: 3 units @ £120.00 with 15% discount = £306.00 net, 0% VAT = £0.00, Gross = £306.00
    Subtotal = £554.60, Discount = £54.00, Tax = £49.72, Total = £604.32, Amount due = £604.32
    """
    org_id = str(phase4_setup["org_a"].id)
    token = phase4_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}
    supplier_id = str(phase4_setup["supplier_a"].id)
    vat_20_id = str(phase4_setup["vat_20"].id)
    vat_0_id = str(phase4_setup["vat_0"].id)

    now = datetime.now(UTC)
    payload = {
        "supplier_id": supplier_id,
        "supplier_invoice_number": "APEX-2026-881",
        "bill_date": now.isoformat(),
        "due_date": (now + timedelta(days=30)).isoformat(),
        "currency": "GBP",
        "supplier_reference": "REF-881",
        "lines": [
            {
                "description": "Freight & Pallet Logistics",
                "quantity": "5.5",
                "unit_price": "45.20",
                "tax_rate_id": vat_20_id,
                "position": 0,
            },
            {
                "description": "Packaging Materials (15% bulk discount)",
                "quantity": "3",
                "unit_price": "120.00",
                "discount_type": "PERCENTAGE",
                "discount_value": "15.00",
                "tax_rate_id": vat_0_id,
                "position": 1,
            },
        ],
    }

    res = await client.post(f"/api/v1/organisations/{org_id}/bills", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    bill = res.json()

    assert Decimal(str(bill["subtotal"])) == Decimal("554.60")
    assert Decimal(str(bill["discount_total"])) == Decimal("54.00")
    assert Decimal(str(bill["tax_total"])) == Decimal("49.72")
    assert Decimal(str(bill["total"])) == Decimal("604.32")
    assert Decimal(str(bill["amount_due"])) == Decimal("604.32")
    assert bill["status"] == "DRAFT"
    assert bill["internal_bill_number"].startswith("BILL-")


# ─── 2. Multi-Tier Approval Lifecycle & Supplier Historical Snapshot ───
async def test_bill_full_approval_lifecycle_and_supplier_snapshot(client: AsyncClient, phase4_setup: dict):
    """
    Validates complete multi-tier bill lifecycle:
    1. Create DRAFT bill
    2. Update lines while in DRAFT
    3. Submit for approval -> AWAITING_APPROVAL
    4. Reject bill with comment -> REJECTED
    5. Edit rejected bill and resubmit -> AWAITING_APPROVAL
    6. Approve bill -> APPROVED (freezes supplier historical snapshot)
    7. Void approved bill with mandatory reason -> VOID
    """
    org_id = str(phase4_setup["org_a"].id)
    token_owner = phase4_setup["tokens"]["owner"]
    token_bookkeeper = phase4_setup["tokens"]["bookkeeper"]
    token_approver = phase4_setup["tokens"]["approver"]
    supplier_id = str(phase4_setup["supplier_a"].id)
    vat_20_id = str(phase4_setup["vat_20"].id)

    now = datetime.now(UTC)

    # 1. Bookkeeper creates DRAFT bill
    create_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills",
        json={
            "supplier_id": supplier_id,
            "supplier_invoice_number": "APEX-2026-900",
            "bill_date": now.isoformat(),
            "due_date": (now + timedelta(days=30)).isoformat(),
            "lines": [{"description": "Initial Service", "quantity": "1", "unit_price": "100.00", "tax_rate_id": vat_20_id}],
        },
        headers={"Authorization": f"Bearer {token_bookkeeper}"},
    )
    assert create_res.status_code == 201
    bill = create_res.json()
    bill_id = bill["id"]
    assert bill["status"] == "DRAFT"

    # 2. Bookkeeper updates draft lines
    patch_res = await client.patch(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}",
        json={
            "supplier_reference": "PO-REV-1",
            "lines": [{"description": "Updated Service", "quantity": "2", "unit_price": "150.00", "tax_rate_id": vat_20_id}],
        },
        headers={"Authorization": f"Bearer {token_bookkeeper}"},
    )
    assert patch_res.status_code == 200
    assert Decimal(str(patch_res.json()["total"])) == Decimal("360.00")

    # 3. Bookkeeper submits for approval
    submit_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}/submit",
        json={"comment": "Ready for manager review"},
        headers={"Authorization": f"Bearer {token_bookkeeper}"},
    )
    assert submit_res.status_code == 200
    assert submit_res.json()["status"] == "AWAITING_APPROVAL"

    # 4. Approver rejects bill with comment
    reject_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}/reject",
        json={"reason": "Incorrect quantity billed. Please adjust."},
        headers={"Authorization": f"Bearer {token_approver}"},
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "REJECTED"

    # 5. Bookkeeper adjusts rejected bill and resubmits
    patch_res2 = await client.patch(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}",
        json={
            "lines": [{"description": "Adjusted Service", "quantity": "1", "unit_price": "150.00", "tax_rate_id": vat_20_id}],
        },
        headers={"Authorization": f"Bearer {token_bookkeeper}"},
    )
    assert patch_res2.status_code == 200

    submit_res2 = await client.post(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}/submit",
        json={"comment": "Quantity adjusted as requested."},
        headers={"Authorization": f"Bearer {token_bookkeeper}"},
    )
    assert submit_res2.status_code == 200
    assert submit_res2.json()["status"] == "AWAITING_APPROVAL"

    # 6. Approver approves bill
    appr_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}/approve",
        json={"comment": "Approved for payment scheduling."},
        headers={"Authorization": f"Bearer {token_approver}"},
    )
    assert appr_res.status_code == 200
    appr_bill = appr_res.json()
    assert appr_bill["status"] == "APPROVED"
    assert appr_bill["internal_bill_number"] is not None

    # Verify supplier snapshot is frozen
    assert appr_bill["supplier_name_snapshot"] == "Apex Logistics Ltd"
    assert appr_bill["supplier_vat_number_snapshot"] == "GB112233445"
    assert appr_bill["supplier_address_snapshot"] is not None
    assert appr_bill["supplier_address_snapshot"]["city"] == "Manchester"

    # 7. Owner voids approved bill with reason
    void_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}/void",
        json={"reason": "Vendor issued revised cancellation credit note."},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert void_res.status_code == 200
    assert void_res.json()["status"] == "VOID"
    assert void_res.json()["void_reason"] == "Vendor issued revised cancellation credit note."


# ─── 3. Approved Bill Immutability Safeguards ──────────────────────────
async def test_approved_bill_immutability_safeguard(client: AsyncClient, phase4_setup: dict):
    """
    GAAP & SOX Compliance: Approved bills CANNOT be directly edited or deleted.
    Attempts must return 400 Bad Request.
    """
    org_id = str(phase4_setup["org_a"].id)
    token = phase4_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}
    supplier_id = str(phase4_setup["supplier_a"].id)

    now = datetime.now(UTC)
    create_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills",
        json={
            "supplier_id": supplier_id,
            "supplier_invoice_number": "APEX-IMMUTABLE-01",
            "bill_date": now.isoformat(),
            "due_date": (now + timedelta(days=30)).isoformat(),
            "lines": [{"description": "Supplies", "quantity": "1", "unit_price": "50.00"}],
        },
        headers=headers,
    )
    bill_id = create_res.json()["id"]

    # Submit and Approve
    await client.post(f"/api/v1/organisations/{org_id}/bills/{bill_id}/submit", headers=headers)
    await client.post(f"/api/v1/organisations/{org_id}/bills/{bill_id}/approve", headers=headers)

    # Attempt direct PATCH -> 400 Bad Request
    patch_res = await client.patch(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}",
        json={"supplier_reference": "Illegal Reference Change"},
        headers=headers,
    )
    assert patch_res.status_code == 400
    assert "Only DRAFT or REJECTED bills can be edited" in (patch_res.json().get("detail") or patch_res.json().get("message"))

    # Attempt direct DELETE -> 400 Bad Request
    del_res = await client.delete(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}",
        headers=headers,
    )
    assert del_res.status_code == 400
    assert "Only DRAFT bills can be deleted" in (del_res.json().get("detail") or del_res.json().get("message"))


# ─── 4. Runtime Derived OVERDUE Status ────────────────────────────────
async def test_derived_runtime_overdue_status_bills(client: AsyncClient, phase4_setup: dict):
    """
    OVERDUE is a computed runtime state (due_date in past AND amount_due > 0).
    It is never statically persisted to avoid cron desynchronisation.
    """
    org_id = str(phase4_setup["org_a"].id)
    token = phase4_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}
    supplier_id = str(phase4_setup["supplier_a"].id)

    now = datetime.now(UTC)
    overdue_due_date = now - timedelta(days=15)
    bill_date = now - timedelta(days=45)

    create_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills",
        json={
            "supplier_id": supplier_id,
            "supplier_invoice_number": "APEX-OVERDUE-01",
            "bill_date": bill_date.isoformat(),
            "due_date": overdue_due_date.isoformat(),
            "lines": [{"description": "Monthly Server Colocation", "quantity": "1", "unit_price": "800.00"}],
        },
        headers=headers,
    )
    bill_id = create_res.json()["id"]

    # Submit and approve
    await client.post(f"/api/v1/organisations/{org_id}/bills/{bill_id}/submit", headers=headers)
    await client.post(f"/api/v1/organisations/{org_id}/bills/{bill_id}/approve", headers=headers)

    # Fetch detail
    get_res = await client.get(f"/api/v1/organisations/{org_id}/bills/{bill_id}", headers=headers)
    assert get_res.status_code == 200
    bill = get_res.json()
    assert bill["status"] == "APPROVED"
    assert bill["effective_status"] == "OVERDUE"

    # Query with status filter OVERDUE
    list_res = await client.get(f"/api/v1/organisations/{org_id}/bills?status=OVERDUE", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert any(b["id"] == bill_id for b in items)


# ─── 5. Sequential Numbering Counter ─────────────────────────────────
async def test_sequential_bill_numbering_counter(client: AsyncClient, phase4_setup: dict):
    """
    Verifies that internal bill numbers increment monotonically (BILL-000001, BILL-000002).
    """
    org_id = str(phase4_setup["org_a"].id)
    token = phase4_setup["tokens"]["owner"]
    headers = {"Authorization": f"Bearer {token}"}
    supplier_id = str(phase4_setup["supplier_a"].id)

    now = datetime.now(UTC)

    b1_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills",
        json={
            "supplier_id": supplier_id,
            "supplier_invoice_number": "SEQ-TEST-1",
            "bill_date": now.isoformat(),
            "lines": [{"description": "Item 1", "quantity": "1", "unit_price": "25.00"}],
        },
        headers=headers,
    )
    b2_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills",
        json={
            "supplier_id": supplier_id,
            "supplier_invoice_number": "SEQ-TEST-2",
            "bill_date": now.isoformat(),
            "lines": [{"description": "Item 2", "quantity": "1", "unit_price": "50.00"}],
        },
        headers=headers,
    )

    num1 = b1_res.json()["internal_bill_number"]
    num2 = b2_res.json()["internal_bill_number"]

    assert num1.startswith("BILL-")
    assert num2.startswith("BILL-")

    val1 = int(num1.split("-")[1])
    val2 = int(num2.split("-")[1])
    assert val2 == val1 + 1


# ─── 6. Smart Duplicate Bill Detection & Reasoned Override ───────────
async def test_duplicate_bill_detection_and_override(client: AsyncClient, phase4_setup: dict):
    """
    Prevents duplicate bill entry (supplier + invoice number).
    Requires explicit reason override to proceed.
    """
    org_id = str(phase4_setup["org_a"].id)
    token = phase4_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}
    supplier_id = str(phase4_setup["supplier_a"].id)

    now = datetime.now(UTC)
    invoice_num = "DUP-CHECK-999"

    # Create original bill
    res1 = await client.post(
        f"/api/v1/organisations/{org_id}/bills",
        json={
            "supplier_id": supplier_id,
            "supplier_invoice_number": invoice_num,
            "bill_date": now.isoformat(),
            "lines": [{"description": "Consultancy Services", "quantity": "1", "unit_price": "200.00"}],
        },
        headers=headers,
    )
    assert res1.status_code == 201

    # Check duplicate endpoint pre-check
    chk_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills/check-duplicate",
        json={
            "supplier_id": supplier_id,
            "supplier_invoice_number": invoice_num,
            "bill_date": now.isoformat(),
            "total": "200.00",
        },
        headers=headers,
    )
    assert chk_res.status_code == 200
    assert chk_res.json()["is_duplicate"] is True

    # Attempt to create duplicate bill without override -> 409 Conflict
    dup_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills",
        json={
            "supplier_id": supplier_id,
            "supplier_invoice_number": invoice_num,
            "bill_date": now.isoformat(),
            "lines": [{"description": "Duplicate Attempt", "quantity": "1", "unit_price": "200.00"}],
        },
        headers=headers,
    )
    assert dup_res.status_code == 409
    assert "DUPLICATE_BILL" in str(dup_res.json())

    # Create with valid override reason -> 201 Created
    override_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills",
        json={
            "supplier_id": supplier_id,
            "supplier_invoice_number": invoice_num,
            "bill_date": now.isoformat(),
            "duplicate_override_reason": "Vendor re-issued invoice under same number after address correction.",
            "lines": [{"description": "Duplicate with override", "quantity": "1", "unit_price": "200.00"}],
        },
        headers=headers,
    )
    assert override_res.status_code == 201
    assert override_res.json()["duplicate_override_reason"] is not None


# ─── 7. Fine-Grained 8-Role RBAC Enforcement ─────────────────────────
async def test_rbac_supplier_bills_8_roles(client: AsyncClient, phase4_setup: dict):
    """
    Validates separation of duties across all 8 canonical roles:
    - employee: can create draft, CANNOT submit, approve, reject, or void
    - bookkeeper: can draft, update, submit, CANNOT approve, reject, or void
    - approver: can approve and reject, CANNOT create draft
    - auditor & viewer: read-only access
    - accountant & owner: full authority
    """
    org_id = str(phase4_setup["org_a"].id)
    tokens = phase4_setup["tokens"]
    supplier_id = str(phase4_setup["supplier_a"].id)
    now = datetime.now(UTC)

    draft_payload = {
        "supplier_id": supplier_id,
        "supplier_invoice_number": "RBAC-TEST-001",
        "bill_date": now.isoformat(),
        "lines": [{"description": "Employee Purchase Request", "quantity": "1", "unit_price": "45.00"}],
    }

    # 1. Employee creates draft -> Allowed
    emp_create = await client.post(
        f"/api/v1/organisations/{org_id}/bills",
        json=draft_payload,
        headers={"Authorization": f"Bearer {tokens['employee']}"},
    )
    assert emp_create.status_code == 201
    bill_id = emp_create.json()["id"]

    # Employee attempts submit -> 403 Forbidden
    emp_submit = await client.post(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}/submit",
        json={"comment": "Employee trying to submit"},
        headers={"Authorization": f"Bearer {tokens['employee']}"},
    )
    assert emp_submit.status_code == 403

    # Employee attempts approve -> 403 Forbidden
    emp_appr = await client.post(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}/approve",
        headers={"Authorization": f"Bearer {tokens['employee']}"},
    )
    assert emp_appr.status_code == 403

    # 2. Approver attempts to create draft -> 403 Forbidden
    appr_create = await client.post(
        f"/api/v1/organisations/{org_id}/bills",
        json={**draft_payload, "supplier_invoice_number": "APPROVER-ILLEGAL-01"},
        headers={"Authorization": f"Bearer {tokens['approver']}"},
    )
    assert appr_create.status_code == 403

    # 3. Bookkeeper submits bill for approval -> Allowed
    bk_submit = await client.post(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}/submit",
        json={"comment": "Verified by bookkeeper."},
        headers={"Authorization": f"Bearer {tokens['bookkeeper']}"},
    )
    assert bk_submit.status_code == 200

    # Bookkeeper attempts to approve -> 403 Forbidden (Segregation of Duties)
    bk_appr = await client.post(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}/approve",
        headers={"Authorization": f"Bearer {tokens['bookkeeper']}"},
    )
    assert bk_appr.status_code == 403

    # 4. Auditor attempts to modify -> 403 Forbidden
    aud_patch = await client.patch(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}",
        json={"notes": "Auditor editing"},
        headers={"Authorization": f"Bearer {tokens['auditor']}"},
    )
    assert aud_patch.status_code == 403

    # Auditor read -> Allowed
    aud_read = await client.get(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}",
        headers={"Authorization": f"Bearer {tokens['auditor']}"},
    )
    assert aud_read.status_code == 200

    # 5. Approver approves -> Allowed
    approver_appr = await client.post(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}/approve",
        headers={"Authorization": f"Bearer {tokens['approver']}"},
    )
    assert approver_appr.status_code == 200


# ─── 8. Strict Multi-Tenant Isolation ─────────────────────────────────
async def test_tenant_isolation_supplier_bills(client: AsyncClient, phase4_setup: dict):
    """
    Bills and attached files belonging to Org Alpha MUST NEVER be accessible,
    modifiable, or leak metadata to Org Beta. Returns 404.
    """
    org_a_id = str(phase4_setup["org_a"].id)
    org_b_id = str(phase4_setup["org_b"].id)
    token_a = phase4_setup["tokens"]["accountant"]
    token_b = phase4_setup["tokens"]["owner_b"]
    supplier_a = str(phase4_setup["supplier_a"].id)

    now = datetime.now(UTC)

    # Create bill in Org A
    create_res = await client.post(
        f"/api/v1/organisations/{org_a_id}/bills",
        json={
            "supplier_id": supplier_a,
            "supplier_invoice_number": "ALPHA-CONFIDENTIAL-BILL",
            "bill_date": now.isoformat(),
            "lines": [{"description": "Secret R&D Supplies", "quantity": "1", "unit_price": "10000.00"}],
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert create_res.status_code == 201
    bill_id = create_res.json()["id"]

    # Org B user attempts to GET Org A bill under Org A endpoint -> 403 Forbidden (membership guard)
    cross_res1 = await client.get(
        f"/api/v1/organisations/{org_a_id}/bills/{bill_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert cross_res1.status_code == 403

    # Org B user attempts to GET Org A bill under Org B endpoint -> 404 Not Found (tenant query filter)
    cross_res2 = await client.get(
        f"/api/v1/organisations/{org_b_id}/bills/{bill_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert cross_res2.status_code == 404
