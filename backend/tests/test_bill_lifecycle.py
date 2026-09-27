"""
Warp Ladger — Bill Lifecycle & Workflow Tests (Phase 4)
Tests:
- DRAFT -> AWAITING_APPROVAL -> REJECTED -> edit -> resubmit
- AWAITING_APPROVAL -> APPROVED (supplier snapshot, status lock)
- Prevention of editing or deleting approved bills
- Voiding approved bills with reason
- Runtime OVERDUE status derivation
"""
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from httpx import AsyncClient

from app.database.models import Contact, ContactAddress, ContactStatus, ContactType


@pytest.mark.asyncio
async def test_full_approval_lifecycle_and_snapshot(client: AsyncClient, test_setup, db_session):
    org_id = test_setup["org_a"].id
    token = test_setup["token_a"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create supplier with address
    supplier = Contact(
        id=uuid.uuid4(),
        organisation_id=org_id,
        business_name="Acme Suppliers Ltd",
        contact_type=ContactType.SUPPLIER,
        status=ContactStatus.ACTIVE,
        email="orders@acmesuppliers.co.uk",
        vat_number="GB999888777",
    )
    addr = ContactAddress(
        id=uuid.uuid4(),
        organisation_id=org_id,
        contact_id=supplier.id,
        line1="10 Downing Street",
        city="London",
        postcode="SW1A 2AA",
        country_code="GB",
        is_primary=True,
    )
    db_session.add_all([supplier, addr])
    await db_session.commit()

    # 1. Create Draft
    create_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills",
        json={
            "supplier_id": str(supplier.id),
            "supplier_invoice_number": "ACM-902",
            "bill_date": "2026-09-18T10:00:00Z",
            "lines": [{"description": "Office Supplies", "quantity": "5", "unit_price": "20.00"}],
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    bill_id = create_res.json()["id"]

    # 2. Submit for approval
    sub_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}/submit",
        json={"comment": "Ready for manager review"},
        headers=headers,
    )
    assert sub_res.status_code == 200
    assert sub_res.json()["status"] == "AWAITING_APPROVAL"

    # 3. Reject with reason
    rej_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}/reject",
        json={"reason": "Missing supporting purchase order reference."},
        headers=headers,
    )
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == "REJECTED"
    assert rej_res.json()["rejection_reason"] == "Missing supporting purchase order reference."

    # 4. Edit rejected bill to fix issues
    patch_res = await client.patch(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}",
        json={"purchase_order_reference": "PO-2026-889"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["purchase_order_reference"] == "PO-2026-889"

    # 5. Resubmit for approval
    resub_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}/submit",
        json={"comment": "Added PO number as requested"},
        headers=headers,
    )
    assert resub_res.status_code == 200
    assert resub_res.json()["status"] == "AWAITING_APPROVAL"

    # 6. Approve bill
    app_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}/approve",
        json={"comment": "Verified and approved for payment"},
        headers=headers,
    )
    assert app_res.status_code == 200
    approved_bill = app_res.json()
    assert approved_bill["status"] == "APPROVED"
    assert approved_bill["effective_status"] == "AWAITING_PAYMENT"

    # Verify supplier snapshot was preserved
    assert approved_bill["supplier_name_snapshot"] == "Acme Suppliers Ltd"
    assert approved_bill["supplier_email_snapshot"] == "orders@acmesuppliers.co.uk"
    assert approved_bill["supplier_vat_number_snapshot"] == "GB999888777"
    assert approved_bill["supplier_address_snapshot"]["postal_code"] == "SW1A 2AA"

    # 7. Changing original supplier record does NOT alter snapshot
    supplier.business_name = "Changed Business Name Ltd"
    await db_session.commit()

    re_get = await client.get(f"/api/v1/organisations/{org_id}/bills/{bill_id}", headers=headers)
    assert re_get.json()["supplier_name_snapshot"] == "Acme Suppliers Ltd"

    # 8. Approved bills cannot be directly edited or deleted
    edit_fail = await client.patch(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}",
        json={"supplier_invoice_number": "NEW-INV-1"},
        headers=headers,
    )
    assert edit_fail.status_code == 400
    assert "cannot be edited directly" in edit_fail.text

    del_fail = await client.delete(f"/api/v1/organisations/{org_id}/bills/{bill_id}", headers=headers)
    assert del_fail.status_code == 400
    assert "Only DRAFT bills can be deleted" in del_fail.text

    # 9. Voiding bill requires reason
    void_fail = await client.post(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}/void",
        json={"reason": ""},
        headers=headers,
    )
    assert void_fail.status_code == 422  # validation min_length=3

    void_ok = await client.post(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}/void",
        json={"reason": "Duplicate entered by mistake, verified with supplier"},
        headers=headers,
    )
    assert void_ok.status_code == 200
    assert void_ok.json()["status"] == "VOID"
    assert float(void_ok.json()["amount_due"]) == 0.0


@pytest.mark.asyncio
async def test_overdue_dynamic_status_derivation(client: AsyncClient, test_setup, db_session):
    org_id = test_setup["org_a"].id
    token = test_setup["token_a"]
    headers = {"Authorization": f"Bearer {token}"}

    supplier = Contact(
        id=uuid.uuid4(),
        organisation_id=org_id,
        business_name="Power Utilities",
        contact_type=ContactType.SUPPLIER,
        status=ContactStatus.ACTIVE,
    )
    db_session.add(supplier)
    await db_session.commit()

    # Past due date (overdue)
    past_due = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    past_bill = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()

    create_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills",
        json={
            "supplier_id": str(supplier.id),
            "supplier_invoice_number": "ELEC-2026-08",
            "bill_date": past_bill,
            "due_date": past_due,
            "lines": [{"description": "Electricity", "quantity": "1", "unit_price": "500.00"}],
        },
        headers=headers,
    )
    bill_id = create_res.json()["id"]

    # In draft, status is DRAFT (not overdue yet)
    assert create_res.json()["effective_status"] == "DRAFT"

    # Submit and approve
    await client.post(f"/api/v1/organisations/{org_id}/bills/{bill_id}/submit", headers=headers)
    app_res = await client.post(f"/api/v1/organisations/{org_id}/bills/{bill_id}/approve", headers=headers)
    assert app_res.status_code == 200

    # Once approved, since current_time > due_date and amount_due > 0, effective status is OVERDUE
    assert app_res.json()["status"] == "APPROVED"
    assert app_res.json()["effective_status"] == "OVERDUE"

    # Verify list endpoint also derives OVERDUE
    list_res = await client.get(f"/api/v1/organisations/{org_id}/bills?status=OVERDUE", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert any(b["id"] == bill_id for b in items)
