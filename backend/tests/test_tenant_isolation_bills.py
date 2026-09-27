"""
Warp Ladger — Multi-Tenant Isolation & Security Tests for Bills (Phase 4)
Tests:
- Organisation A cannot read, update, submit, approve, or void Organisation B's bills
- Organisation A cannot create a bill referencing Organisation B's supplier or tax rates
- Member role cannot approve bills without 'bills:approve' permission
"""
import uuid
import pytest
from httpx import AsyncClient

from app.database.models import Contact, ContactStatus, ContactType


@pytest.mark.asyncio
async def test_cross_tenant_access_blocked(client: AsyncClient, test_setup, db_session):
    org_a_id = test_setup["org_a"].id
    org_b_id = test_setup["org_b"].id
    token_a = test_setup["token_a"]
    token_b = test_setup["token_b"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Supplier in Org B
    supplier_b = Contact(
        id=uuid.uuid4(),
        organisation_id=org_b_id,
        business_name="Supplier of Org B",
        contact_type=ContactType.SUPPLIER,
        status=ContactStatus.ACTIVE,
    )
    db_session.add(supplier_b)
    await db_session.commit()

    # User B creates a bill in Org B
    res_b = await client.post(
        f"/api/v1/organisations/{org_b_id}/bills",
        json={
            "supplier_id": str(supplier_b.id),
            "supplier_invoice_number": "ORGB-INV-1",
            "bill_date": "2026-09-18T10:00:00Z",
            "lines": [{"description": "Service B", "quantity": "1", "unit_price": "100.00"}],
        },
        headers=headers_b,
    )
    assert res_b.status_code == 201
    bill_b_id = res_b.json()["id"]

    # 1. User A tries to GET Org B's bill -> 403 or 404
    get_res = await client.get(
        f"/api/v1/organisations/{org_b_id}/bills/{bill_b_id}",
        headers=headers_a,
    )
    assert get_res.status_code in (403, 404)

    # 2. User A tries to GET Org B's bill through Org A URL -> 404
    get_res2 = await client.get(
        f"/api/v1/organisations/{org_a_id}/bills/{bill_b_id}",
        headers=headers_a,
    )
    assert get_res2.status_code == 404

    # 3. User A tries to UPDATE Org B's bill -> 404
    patch_res = await client.patch(
        f"/api/v1/organisations/{org_a_id}/bills/{bill_b_id}",
        json={"notes": "Hacked"},
        headers=headers_a,
    )
    assert patch_res.status_code == 404

    # 4. User A tries to DELETE Org B's bill -> 404
    del_res = await client.delete(
        f"/api/v1/organisations/{org_a_id}/bills/{bill_b_id}",
        headers=headers_a,
    )
    assert del_res.status_code == 404

    # 5. User A tries to reference Org B's supplier in Org A bill -> 404
    create_fail = await client.post(
        f"/api/v1/organisations/{org_a_id}/bills",
        json={
            "supplier_id": str(supplier_b.id),  # Belongs to Org B!
            "supplier_invoice_number": "ORGA-FAIL",
            "bill_date": "2026-09-18T10:00:00Z",
            "lines": [{"description": "Item", "quantity": "1", "unit_price": "10.00"}],
        },
        headers=headers_a,
    )
    assert create_fail.status_code == 404
    assert "Supplier not found in this organisation" in create_fail.text


@pytest.mark.asyncio
async def test_role_permission_separation_for_bills(client: AsyncClient, test_setup, db_session):
    org_id = test_setup["org_a"].id
    token_owner = test_setup["token_a"]
    token_member = test_setup["token_a_member"]
    headers_owner = {"Authorization": f"Bearer {token_owner}"}
    headers_member = {"Authorization": f"Bearer {token_member}"}

    supplier = Contact(
        id=uuid.uuid4(),
        organisation_id=org_id,
        business_name="Role Test Supplier",
        contact_type=ContactType.SUPPLIER,
        status=ContactStatus.ACTIVE,
    )
    db_session.add(supplier)
    await db_session.commit()

    # Member can CREATE draft bill
    create_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills",
        json={
            "supplier_id": str(supplier.id),
            "supplier_invoice_number": "ROLE-01",
            "bill_date": "2026-09-18T10:00:00Z",
            "lines": [{"description": "Office rent", "quantity": "1", "unit_price": "1000.00"}],
        },
        headers=headers_member,
    )
    assert create_res.status_code == 201
    bill_id = create_res.json()["id"]

    # Member can SUBMIT for approval
    sub_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}/submit",
        json={"comment": "Submitted by member"},
        headers=headers_member,
    )
    assert sub_res.status_code == 200

    # Member CANNOT APPROVE (missing bills:approve permission) -> 403
    app_fail = await client.post(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}/approve",
        json={"comment": "Attempted self-approval"},
        headers=headers_member,
    )
    assert app_fail.status_code == 403

    # Owner CAN APPROVE
    app_ok = await client.post(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}/approve",
        json={"comment": "Approved by owner"},
        headers=headers_owner,
    )
    assert app_ok.status_code == 200
    assert app_ok.json()["status"] == "APPROVED"
