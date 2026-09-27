"""
Warp Ladger — Bill CRUD & Calculation Tests (Phase 4)
Tests:
- Creating a draft bill
- Financial calculation accuracy (VAT, decimal quantities, discounts)
- Rejection of invalid supplier types (customers cannot be billed)
- Updating lines & recalculation of totals
- Optimistic locking conflict detection
- Deleting a draft bill
"""
from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient

from app.database.models import Contact, ContactStatus, ContactType, TaxRate, TaxType


@pytest.mark.asyncio
async def test_create_and_read_draft_bill(client: AsyncClient, test_setup, db_session):
    org_id = test_setup["org_a"].id
    token = test_setup["token_a"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a supplier contact
    supplier = Contact(
        id=uuid.uuid4(),
        organisation_id=org_id,
        business_name="Microsoft Limited",
        contact_type=ContactType.SUPPLIER,
        status=ContactStatus.ACTIVE,
        email="billing@microsoft.com",
        vat_number="GB123456789",
    )
    # Create standard 20% tax rate
    tax_rate = TaxRate(
        id=uuid.uuid4(),
        organisation_id=org_id,
        name="Standard VAT 20%",
        code="VAT20",
        rate=Decimal("20.0000"),
        tax_type=TaxType.STANDARD,
        active=True,
    )
    db_session.add_all([supplier, tax_rate])
    await db_session.commit()

    # 2. POST /bills
    payload = {
        "supplier_id": str(supplier.id),
        "supplier_invoice_number": "MS-882931",
        "bill_date": "2026-09-18T10:00:00Z",
        "currency": "GBP",
        "notes": "Office 365 Enterprise",
        "lines": [
            {
                "description": "Microsoft 365 Business Standard (10 users)",
                "quantity": "10.0000",
                "unit_price": "20.0000",
                "tax_rate_id": str(tax_rate.id),
                "discount_type": "PERCENTAGE",
                "discount_value": "10.0000",  # 10% discount on £200 = £20 discount => net £180
            },
            {
                "description": "Azure Cloud Services",
                "quantity": "1.5000",
                "unit_price": "100.0000",  # 1.5 * 100 = net £150
                "tax_rate_id": str(tax_rate.id),
            },
        ],
    }

    res = await client.post(f"/api/v1/organisations/{org_id}/bills", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["supplier_invoice_number"] == "MS-882931"
    assert data["internal_bill_number"].startswith("BILL-")
    assert data["status"] == "DRAFT"

    # Line 1: net 180, tax 36 (20%), gross 216
    # Line 2: net 150, tax 30 (20%), gross 180
    # Total: net 330, tax 66, total 396
    assert float(data["subtotal"]) == 330.00
    assert float(data["tax_total"]) == 66.00
    assert float(data["total"]) == 396.00
    assert float(data["amount_due"]) == 396.00
    assert float(data["discount_total"]) == 20.00

    bill_id = data["id"]

    # 3. GET /bills/{id}
    get_res = await client.get(f"/api/v1/organisations/{org_id}/bills/{bill_id}", headers=headers)
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert len(get_data["lines"]) == 2
    assert get_data["effective_status"] == "DRAFT"


@pytest.mark.asyncio
async def test_invalid_supplier_type_rejected(client: AsyncClient, test_setup, db_session):
    org_id = test_setup["org_a"].id
    token = test_setup["token_a"]
    headers = {"Authorization": f"Bearer {token}"}

    # Customer only contact
    customer = Contact(
        id=uuid.uuid4(),
        organisation_id=org_id,
        business_name="Customer Ltd",
        contact_type=ContactType.CUSTOMER,
        status=ContactStatus.ACTIVE,
    )
    db_session.add(customer)
    await db_session.commit()

    payload = {
        "supplier_id": str(customer.id),
        "supplier_invoice_number": "CUST-001",
        "bill_date": "2026-09-18T10:00:00Z",
        "lines": [{"description": "Product", "quantity": "1", "unit_price": "50"}],
    }

    res = await client.post(f"/api/v1/organisations/{org_id}/bills", json=payload, headers=headers)
    assert res.status_code == 400
    assert "not classified as a supplier" in res.text


@pytest.mark.asyncio
async def test_update_draft_and_optimistic_locking(client: AsyncClient, test_setup, db_session):
    org_id = test_setup["org_a"].id
    token = test_setup["token_a"]
    headers = {"Authorization": f"Bearer {token}"}

    supplier = Contact(
        id=uuid.uuid4(),
        organisation_id=org_id,
        business_name="Hardware Direct",
        contact_type=ContactType.SUPPLIER,
        status=ContactStatus.ACTIVE,
    )
    db_session.add(supplier)
    await db_session.commit()

    # Create bill
    res = await client.post(
        f"/api/v1/organisations/{org_id}/bills",
        json={
            "supplier_id": str(supplier.id),
            "supplier_invoice_number": "HD-1001",
            "bill_date": "2026-09-18T10:00:00Z",
            "lines": [{"description": "Keyboard", "quantity": "2", "unit_price": "25.00"}],
        },
        headers=headers,
    )
    assert res.status_code == 201
    bill = res.json()
    bill_id = bill["id"]
    assert bill["version"] == 1
    assert float(bill["total"]) == 50.00

    # 1. Update lines
    patch_res = await client.patch(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}",
        json={
            "version": 1,
            "lines": [
                {"description": "Keyboard", "quantity": "3", "unit_price": "25.00"},
                {"description": "Mouse", "quantity": "1", "unit_price": "15.00"},
            ],
        },
        headers=headers,
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["version"] == 2
    assert float(updated["total"]) == 90.00  # 3*25 + 15 = 90

    # 2. Concurrency Conflict: try updating with old version=1
    conflict_res = await client.patch(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}",
        json={"version": 1, "notes": "Stale edit"},
        headers=headers,
    )
    assert conflict_res.status_code == 409
    assert "changed since you opened it" in conflict_res.text


@pytest.mark.asyncio
async def test_delete_draft_bill(client: AsyncClient, test_setup, db_session):
    org_id = test_setup["org_a"].id
    token = test_setup["token_a"]
    headers = {"Authorization": f"Bearer {token}"}

    supplier = Contact(
        id=uuid.uuid4(),
        organisation_id=org_id,
        business_name="Cleaner Co",
        contact_type=ContactType.SUPPLIER,
        status=ContactStatus.ACTIVE,
    )
    db_session.add(supplier)
    await db_session.commit()

    res = await client.post(
        f"/api/v1/organisations/{org_id}/bills",
        json={
            "supplier_id": str(supplier.id),
            "supplier_invoice_number": "CLN-01",
            "bill_date": "2026-09-18T10:00:00Z",
            "lines": [{"description": "Cleaning", "quantity": "1", "unit_price": "80"}],
        },
        headers=headers,
    )
    bill_id = res.json()["id"]

    del_res = await client.delete(f"/api/v1/organisations/{org_id}/bills/{bill_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify deleted
    get_res = await client.get(f"/api/v1/organisations/{org_id}/bills/{bill_id}", headers=headers)
    assert get_res.status_code == 404
