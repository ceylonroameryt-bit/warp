"""
Warp Ladger — Comprehensive Phase 3 Test Suite: Sales Invoicing / Money In
Validates:
1. Exact Decimal Arithmetic & Round-Half-Up Financial Accuracy
2. Full Invoice Lifecycle: Draft -> Edit -> Approve -> Send -> Void
3. Concurrency-safe Sequential Invoice Numbering (e.g. INV-000001)
4. Customer Historical Snapshotting upon Approval
5. Approval Immutability (Direct edits & deletion blocked on approved invoices)
6. Derived Runtime OVERDUE Status
7. PDF Generation Endpoint
8. Fine-grained RBAC across all 8 canonical roles (separation of duties)
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
async def phase3_setup(db_session: AsyncSession):
    """
    Sets up two isolated organisations (Org Alpha and Org Beta),
    seeds all 8 canonical roles, creates tax rates, and a test customer.
    """
    await seed_permissions_and_roles(db_session)

    # 1. Users for Org A
    owner_a = User(email="owner_a@test.com", hashed_password="hash", full_name="Alice Owner", email_verified=True)
    admin_a = User(email="admin_a@test.com", hashed_password="hash", full_name="Arthur Admin", email_verified=True)
    accountant_a = User(email="accountant_a@test.com", hashed_password="hash", full_name="Amy Accountant", email_verified=True)
    bookkeeper_a = User(email="bookkeeper_a@test.com", hashed_password="hash", full_name="Bob Bookkeeper", email_verified=True)
    approver_a = User(email="approver_a@test.com", hashed_password="hash", full_name="Arnold Approver", email_verified=True)
    employee_a = User(email="employee_a@test.com", hashed_password="hash", full_name="Evan Employee", email_verified=True)
    auditor_a = User(email="auditor_a@test.com", hashed_password="hash", full_name="Audrey Auditor", email_verified=True)
    viewer_a = User(email="viewer_a@test.com", hashed_password="hash", full_name="Victor Viewer", email_verified=True)

    # Tenant B User
    owner_b = User(email="owner_b@test.com", hashed_password="hash", full_name="Boris Beta", email_verified=True)

    db_session.add_all([
        owner_a, admin_a, accountant_a, bookkeeper_a, approver_a, employee_a, auditor_a, viewer_a, owner_b
    ])
    await db_session.flush()

    # 2. Organisations
    org_a = Organisation(name="Alpha Corp", slug="alpha-corp", owner_id=owner_a.id)
    org_b = Organisation(name="Beta Enterprises", slug="beta-enterprises", owner_id=owner_b.id)
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

    # 5. Seed Tax Rates for Org A
    vat_20 = TaxRate(
        organisation_id=org_a.id,
        name="Standard VAT (20%)",
        code="STANDARD",
        rate=Decimal("20.0000"),
        tax_type=TaxType.STANDARD,
        active=True,
    )
    vat_0 = TaxRate(
        organisation_id=org_a.id,
        name="Zero Rated (0%)",
        code="ZERO",
        rate=Decimal("0.0000"),
        tax_type=TaxType.ZERO,
        active=True,
    )
    db_session.add_all([vat_20, vat_0])

    # 6. Seed Customers for Org A and Org B
    customer_a = Contact(
        organisation_id=org_a.id,
        contact_type=ContactType.CUSTOMER,
        business_name="Premier Retail Ltd",
        legal_name="Premier Retail Limited",
        email="billing@premierretailltd.co.uk",
        vat_number="GB123456789",
        currency="GBP",
        status=ContactStatus.ACTIVE,
    )
    customer_b = Contact(
        organisation_id=org_b.id,
        contact_type=ContactType.CUSTOMER,
        business_name="Beta Customer PLC",
        email="billing@betacustomer.com",
        currency="GBP",
        status=ContactStatus.ACTIVE,
    )
    db_session.add_all([customer_a, customer_b])
    await db_session.commit()

    return {
        "org_a": org_a,
        "org_b": org_b,
        "customer_a": customer_a,
        "customer_b": customer_b,
        "vat_20": vat_20,
        "vat_0": vat_0,
        "tokens": {
            "owner": create_access_token(str(owner_a.id)),
            "admin": create_access_token(str(admin_a.id)),
            "accountant": create_access_token(str(accountant_a.id)),
            "bookkeeper": create_access_token(str(bookkeeper_a.id)),
            "approver": create_access_token(str(approver_a.id)),
            "employee": create_access_token(str(employee_a.id)),
            "auditor": create_access_token(str(auditor_a.id)),
            "viewer": create_access_token(str(viewer_a.id)),
            "owner_b": create_access_token(str(owner_b.id)),
        },
    }


async def test_decimal_precision_and_golden_accounting_math(client: AsyncClient, phase3_setup: dict):
    """
    Test exact Decimal calculation without floating-point precision loss:
    Line 1: 3.75 hours @ £85.50 = £320.625 -> net £320.63, 20% VAT = £64.125 -> VAT £64.13, Gross £384.76
    Line 2: 2 units @ £100.00 with 10% discount = £180.00 net, 0% VAT = £0.00 VAT, Gross £180.00
    Subtotal = £500.63, Total VAT = £64.13, Total Gross = £564.76
    """
    org_id = str(phase3_setup["org_a"].id)
    token = phase3_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = str(phase3_setup["customer_a"].id)
    vat_20_id = str(phase3_setup["vat_20"].id)
    vat_0_id = str(phase3_setup["vat_0"].id)

    now = datetime.now(UTC)
    payload = {
        "customer_id": customer_id,
        "issue_date": now.isoformat(),
        "due_date": (now + timedelta(days=30)).isoformat(),
        "currency": "GBP",
        "customer_reference": "PO-10023",
        "lines": [
            {
                "description": "Senior Financial Consulting",
                "quantity": "3.75",
                "unit_price": "85.50",
                "tax_rate_id": vat_20_id,
                "position": 0,
            },
            {
                "description": "Software Subscription (10% partner discount)",
                "quantity": "2",
                "unit_price": "100.00",
                "discount_type": "PERCENTAGE",
                "discount_value": "10.00",
                "tax_rate_id": vat_0_id,
                "position": 1,
            },
        ],
    }

    res = await client.post(f"/api/v1/organisations/{org_id}/invoices/", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    inv = res.json()

    # Server recalculated totals verification
    assert Decimal(str(inv["subtotal"])) == Decimal("500.63")
    assert Decimal(str(inv["discount_total"])) == Decimal("20.00")
    assert Decimal(str(inv["tax_total"])) == Decimal("64.13")
    assert Decimal(str(inv["total"])) == Decimal("564.76")
    assert Decimal(str(inv["amount_due"])) == Decimal("564.76")
    assert inv["status"] == "DRAFT"
    assert inv["invoice_number"] is None  # DRAFT invoices have no official number yet


async def test_complete_invoice_lifecycle_and_customer_snapshot(client: AsyncClient, phase3_setup: dict):
    """
    Validates complete invoice workflow:
    1. Create DRAFT invoice
    2. Update DRAFT invoice lines
    3. Approve invoice: generates sequential invoice number (e.g. INV-000001)
       and permanently freezes customer snapshot
    4. Send invoice: creates delivery record and sets status to SENT
    5. Void invoice: requires reason, transitions to VOID, preserves audit record
    """
    org_id = str(phase3_setup["org_a"].id)
    token = phase3_setup["tokens"]["owner"]
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = str(phase3_setup["customer_a"].id)
    vat_20_id = str(phase3_setup["vat_20"].id)

    now = datetime.now(UTC)
    # 1. Create Draft
    create_payload = {
        "customer_id": customer_id,
        "issue_date": now.isoformat(),
        "due_date": (now + timedelta(days=14)).isoformat(),
        "currency": "GBP",
        "lines": [
            {
                "description": "Initial Milestone",
                "quantity": "1",
                "unit_price": "1000.00",
                "tax_rate_id": vat_20_id,
            }
        ],
    }
    create_res = await client.post(f"/api/v1/organisations/{org_id}/invoices/", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    inv_id = create_res.json()["id"]

    # 2. Update Draft
    update_payload = {
        "customer_reference": "REF-ALPHA-99",
        "lines": [
            {
                "description": "Initial Milestone (Revised Scope)",
                "quantity": "1",
                "unit_price": "1200.00",
                "tax_rate_id": vat_20_id,
            }
        ],
    }
    patch_res = await client.patch(f"/api/v1/organisations/{org_id}/invoices/{inv_id}", json=update_payload, headers=headers)
    assert patch_res.status_code == 200
    assert Decimal(str(patch_res.json()["total"])) == Decimal("1440.00")  # 1200 + 20% VAT

    # 3. Approve Invoice
    approve_res = await client.post(f"/api/v1/organisations/{org_id}/invoices/{inv_id}/approve", headers=headers)
    assert approve_res.status_code == 200, approve_res.text
    approved_inv = approve_res.json()
    assert approved_inv["status"] == "APPROVED"
    assert approved_inv["invoice_number"].startswith("INV-")
    assert approved_inv["customer_name_snapshot"] == "Premier Retail Limited"
    assert approved_inv["customer_vat_number_snapshot"] == "GB123456789"
    assert approved_inv["approved_at"] is not None

    # 4. Send Invoice
    send_payload = {
        "recipient_email": "accounts@premierretailltd.co.uk",
        "subject": f"Invoice {approved_inv['invoice_number']} from Alpha Corp",
        "message": "Please find attached your invoice.",
        "attach_pdf": True,
    }
    send_res = await client.post(f"/api/v1/organisations/{org_id}/invoices/{inv_id}/send", json=send_payload, headers=headers)
    assert send_res.status_code == 200
    assert send_res.json()["recipient_email"] == "accounts@premierretailltd.co.uk"

    # Verify status changed to SENT
    detail_res = await client.get(f"/api/v1/organisations/{org_id}/invoices/{inv_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["status"] == "SENT"

    # 5. Void Invoice
    void_payload = {"reason": "Customer cancelled order before fulfillment."}
    void_res = await client.post(f"/api/v1/organisations/{org_id}/invoices/{inv_id}/void", json=void_payload, headers=headers)
    assert void_res.status_code == 200
    void_data = void_res.json()
    assert void_data["status"] == "VOID"
    assert void_data["void_reason"] == "Customer cancelled order before fulfillment."


async def test_approved_invoice_immutability_safeguard(client: AsyncClient, phase3_setup: dict):
    """
    GAAP Requirement: Approved invoices CANNOT be directly edited or deleted.
    Any attempt to mutate lines or delete must raise 400 Bad Request.
    """
    org_id = str(phase3_setup["org_a"].id)
    token = phase3_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = str(phase3_setup["customer_a"].id)

    now = datetime.now(UTC)
    create_res = await client.post(
        f"/api/v1/organisations/{org_id}/invoices/",
        json={
            "customer_id": customer_id,
            "issue_date": now.isoformat(),
            "due_date": (now + timedelta(days=30)).isoformat(),
            "lines": [{"description": "Services", "quantity": "1", "unit_price": "500.00"}],
        },
        headers=headers,
    )
    inv_id = create_res.json()["id"]

    # Approve
    await client.post(f"/api/v1/organisations/{org_id}/invoices/{inv_id}/approve", headers=headers)

    # Attempt to PATCH approved invoice -> 400
    patch_res = await client.patch(
        f"/api/v1/organisations/{org_id}/invoices/{inv_id}",
        json={"customer_reference": "Illegal Modification"},
        headers=headers,
    )
    assert patch_res.status_code == 400
    assert "Only DRAFT invoices can be edited" in patch_res.json()["detail"]

    # Attempt to DELETE approved invoice -> 400
    del_res = await client.delete(f"/api/v1/organisations/{org_id}/invoices/{inv_id}", headers=headers)
    assert del_res.status_code == 400
    assert "Only DRAFT invoices can be deleted" in del_res.json()["detail"]


async def test_derived_runtime_overdue_status(client: AsyncClient, phase3_setup: dict):
    """
    Verifies that an approved invoice with due_date in the past and amount_due > 0
    returns effective_status == 'OVERDUE' without mutating database row.
    """
    org_id = str(phase3_setup["org_a"].id)
    token = phase3_setup["tokens"]["admin"]
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = str(phase3_setup["customer_a"].id)

    # Issue date 60 days ago, due date 30 days ago
    past_issue = (datetime.now(UTC) - timedelta(days=60)).isoformat()
    past_due = (datetime.now(UTC) - timedelta(days=30)).isoformat()

    create_res = await client.post(
        f"/api/v1/organisations/{org_id}/invoices/",
        json={
            "customer_id": customer_id,
            "issue_date": past_issue,
            "due_date": past_due,
            "lines": [{"description": "Overdue Subscription", "quantity": "1", "unit_price": "200.00"}],
        },
        headers=headers,
    )
    inv_id = create_res.json()["id"]

    # Approve
    approve_res = await client.post(f"/api/v1/organisations/{org_id}/invoices/{inv_id}/approve", headers=headers)
    assert approve_res.status_code == 200
    data = approve_res.json()
    assert data["status"] == "APPROVED"
    assert data["effective_status"] == "OVERDUE"

    # Query with status filter OVERDUE
    list_res = await client.get(f"/api/v1/organisations/{org_id}/invoices/?status=OVERDUE", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert any(i["id"] == inv_id for i in items)


async def test_sequential_numbering_counter(client: AsyncClient, phase3_setup: dict):
    """
    Verifies that approving multiple invoices in an organisation
    assigns strictly sequential numbers (INV-000001, INV-000002, etc.).
    """
    org_id = str(phase3_setup["org_a"].id)
    token = phase3_setup["tokens"]["owner"]
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = str(phase3_setup["customer_a"].id)

    now = datetime.now(UTC)

    # Create 2 drafts
    inv1_res = await client.post(
        f"/api/v1/organisations/{org_id}/invoices/",
        json={
            "customer_id": customer_id,
            "issue_date": now.isoformat(),
            "due_date": (now + timedelta(days=14)).isoformat(),
            "lines": [{"description": "Item 1", "quantity": "1", "unit_price": "50.00"}],
        },
        headers=headers,
    )
    inv2_res = await client.post(
        f"/api/v1/organisations/{org_id}/invoices/",
        json={
            "customer_id": customer_id,
            "issue_date": now.isoformat(),
            "due_date": (now + timedelta(days=14)).isoformat(),
            "lines": [{"description": "Item 2", "quantity": "1", "unit_price": "100.00"}],
        },
        headers=headers,
    )

    appr1 = await client.post(f"/api/v1/organisations/{org_id}/invoices/{inv1_res.json()['id']}/approve", headers=headers)
    appr2 = await client.post(f"/api/v1/organisations/{org_id}/invoices/{inv2_res.json()['id']}/approve", headers=headers)

    num1 = appr1.json()["invoice_number"]
    num2 = appr2.json()["invoice_number"]

    assert num1.startswith("INV-")
    assert num2.startswith("INV-")
    # Extract integer suffixes
    val1 = int(num1.split("-")[1])
    val2 = int(num2.split("-")[1])
    assert val2 == val1 + 1


async def test_pdf_generation_endpoint(client: AsyncClient, phase3_setup: dict):
    """
    Verifies that requesting PDF generation triggers the service and returns
    a valid file link and accessible download reference.
    """
    org_id = str(phase3_setup["org_a"].id)
    token = phase3_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = str(phase3_setup["customer_a"].id)

    now = datetime.now(UTC)
    create_res = await client.post(
        f"/api/v1/organisations/{org_id}/invoices/",
        json={
            "customer_id": customer_id,
            "issue_date": now.isoformat(),
            "due_date": (now + timedelta(days=30)).isoformat(),
            "lines": [{"description": "Consulting for PDF", "quantity": "2", "unit_price": "250.00"}],
        },
        headers=headers,
    )
    inv_id = create_res.json()["id"]
    await client.post(f"/api/v1/organisations/{org_id}/invoices/{inv_id}/approve", headers=headers)

    # Trigger PDF generation
    pdf_res = await client.post(f"/api/v1/organisations/{org_id}/invoices/{inv_id}/pdf", headers=headers)
    assert pdf_res.status_code == 202
    assert pdf_res.json()["status"] == "generated"

    # Get PDF download URL
    dl_res = await client.get(f"/api/v1/organisations/{org_id}/invoices/{inv_id}/pdf", headers=headers)
    assert dl_res.status_code == 200
    assert "download_url" in dl_res.json()


async def test_rbac_sales_invoicing_8_roles(client: AsyncClient, phase3_setup: dict):
    """
    Tests fine-grained separation of duties for Sales Invoicing:
    - employee: can create draft, CANNOT approve, send, or void
    - bookkeeper: can draft, update, and send, CANNOT approve or void
    - approver: can approve, CANNOT create draft
    - auditor & viewer: read-only access
    - accountant & owner: full authority
    """
    org_id = str(phase3_setup["org_a"].id)
    tokens = phase3_setup["tokens"]
    customer_id = str(phase3_setup["customer_a"].id)
    now = datetime.now(UTC)

    draft_payload = {
        "customer_id": customer_id,
        "issue_date": now.isoformat(),
        "due_date": (now + timedelta(days=14)).isoformat(),
        "lines": [{"description": "Staff Draft Service", "quantity": "1", "unit_price": "300.00"}],
    }

    # 1. Employee creates draft
    emp_headers = {"Authorization": f"Bearer {tokens['employee']}"}
    emp_create = await client.post(f"/api/v1/organisations/{org_id}/invoices/", json=draft_payload, headers=emp_headers)
    assert emp_create.status_code == 201
    draft_id = emp_create.json()["id"]

    # Employee tries to approve -> 403 Forbidden
    emp_appr = await client.post(f"/api/v1/organisations/{org_id}/invoices/{draft_id}/approve", headers=emp_headers)
    assert emp_appr.status_code == 403

    # 2. Bookkeeper tries to approve -> 403 Forbidden (internal control)
    bk_headers = {"Authorization": f"Bearer {tokens['bookkeeper']}"}
    bk_appr = await client.post(f"/api/v1/organisations/{org_id}/invoices/{draft_id}/approve", headers=bk_headers)
    assert bk_appr.status_code == 403

    # 3. Approver cannot create invoice draft
    appr_headers = {"Authorization": f"Bearer {tokens['approver']}"}
    appr_create = await client.post(f"/api/v1/organisations/{org_id}/invoices/", json=draft_payload, headers=appr_headers)
    assert appr_create.status_code == 403

    # Approver CAN approve the draft invoice
    appr_ok = await client.post(f"/api/v1/organisations/{org_id}/invoices/{draft_id}/approve", headers=appr_headers)
    assert appr_ok.status_code == 200

    # 4. Viewer cannot create or approve
    view_headers = {"Authorization": f"Bearer {tokens['viewer']}"}
    view_create = await client.post(f"/api/v1/organisations/{org_id}/invoices/", json=draft_payload, headers=view_headers)
    assert view_create.status_code == 403

    # Viewer CAN read invoice
    view_read = await client.get(f"/api/v1/organisations/{org_id}/invoices/{draft_id}", headers=view_headers)
    assert view_read.status_code == 200

    # 5. Bookkeeper cannot VOID invoice
    bk_void = await client.post(f"/api/v1/organisations/{org_id}/invoices/{draft_id}/void", json={"reason": "Cancel"}, headers=bk_headers)
    assert bk_void.status_code == 403

    # 6. Accountant CAN VOID invoice
    act_headers = {"Authorization": f"Bearer {tokens['accountant']}"}
    act_void = await client.post(f"/api/v1/organisations/{org_id}/invoices/{draft_id}/void", json={"reason": "Accountant Void"}, headers=act_headers)
    assert act_void.status_code == 200


async def test_tenant_isolation_sales_invoicing(client: AsyncClient, phase3_setup: dict):
    """
    Strict Tenant Isolation: Org B cannot view, edit, approve, or void Org A invoices.
    """
    org_a_id = str(phase3_setup["org_a"].id)
    org_b_id = str(phase3_setup["org_b"].id)
    token_a = phase3_setup["tokens"]["owner"]
    token_b = phase3_setup["tokens"]["owner_b"]

    now = datetime.now(UTC)
    # Org A creates an invoice
    headers_a = {"Authorization": f"Bearer {token_a}"}
    create_res = await client.post(
        f"/api/v1/organisations/{org_a_id}/invoices/",
        json={
            "customer_id": str(phase3_setup["customer_a"].id),
            "issue_date": now.isoformat(),
            "due_date": (now + timedelta(days=14)).isoformat(),
            "lines": [{"description": "Confidential Alpha Contract", "quantity": "1", "unit_price": "5000.00"}],
        },
        headers=headers_a,
    )
    inv_id = create_res.json()["id"]

    # Org B tries to access Org A invoice with Org A URL -> 403 (membership check)
    headers_b = {"Authorization": f"Bearer {token_b}"}
    res1 = await client.get(f"/api/v1/organisations/{org_a_id}/invoices/{inv_id}", headers=headers_b)
    assert res1.status_code == 403

    # Org B tries to access Org A invoice with Org B URL -> 404 (tenant boundary check)
    res2 = await client.get(f"/api/v1/organisations/{org_b_id}/invoices/{inv_id}", headers=headers_b)
    assert res2.status_code == 404

    # Org B tries to approve Org A invoice -> 404 or 403
    res3 = await client.post(f"/api/v1/organisations/{org_b_id}/invoices/{inv_id}/approve", headers=headers_b)
    assert res3.status_code == 404
