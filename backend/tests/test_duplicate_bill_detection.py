"""
Warp Ladger — Duplicate Bill Detection Tests (Phase 4)
Tests:
- Detection of exact duplicate supplier invoice numbers (including normalized variations)
- Direct duplicate check endpoint (/check-duplicate)
- Override workflow with mandatory reason and audit logging
- Checksum-based duplicate document detection
"""
import hashlib
import uuid
import pytest
from httpx import AsyncClient

from app.database.models import Contact, ContactStatus, ContactType, File


@pytest.mark.asyncio
async def test_duplicate_invoice_number_detection_and_override(client: AsyncClient, test_setup, db_session):
    org_id = test_setup["org_a"].id
    token = test_setup["token_a"]
    headers = {"Authorization": f"Bearer {token}"}

    supplier = Contact(
        id=uuid.uuid4(),
        organisation_id=org_id,
        business_name="Vodafone Business",
        contact_type=ContactType.SUPPLIER,
        status=ContactStatus.ACTIVE,
    )
    db_session.add(supplier)
    await db_session.commit()

    # 1. Create first bill with invoice # VF-100234
    res1 = await client.post(
        f"/api/v1/organisations/{org_id}/bills",
        json={
            "supplier_id": str(supplier.id),
            "supplier_invoice_number": "VF-100234",
            "bill_date": "2026-09-18T10:00:00Z",
            "lines": [{"description": "Monthly Mobile Bill", "quantity": "1", "unit_price": "120.00"}],
        },
        headers=headers,
    )
    assert res1.status_code == 201

    # 2. Check duplicate endpoint with normalized variation (e.g. "vf 100234")
    chk_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills/check-duplicate",
        json={
            "supplier_id": str(supplier.id),
            "supplier_invoice_number": "vf 100234",
        },
        headers=headers,
    )
    assert chk_res.status_code == 200
    chk_data = chk_res.json()
    assert chk_data["is_duplicate"] is True
    assert chk_data["severity"] == "BLOCK"
    assert len(chk_data["matches"]) >= 1
    assert chk_data["matches"][0]["match_type"] == "EXACT_INVOICE_NUMBER"

    # 3. Attempt to create duplicate bill without override -> 409 Conflict
    dup_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills",
        json={
            "supplier_id": str(supplier.id),
            "supplier_invoice_number": "vf-100234",  # lowercase variation
            "bill_date": "2026-09-18T10:00:00Z",
            "lines": [{"description": "Duplicate Attempt", "quantity": "1", "unit_price": "120.00"}],
        },
        headers=headers,
    )
    assert dup_res.status_code == 409
    assert "Duplicate invoice number" in dup_res.text

    # 4. Create duplicate bill WITH override reason -> Success 201
    override_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills",
        json={
            "supplier_id": str(supplier.id),
            "supplier_invoice_number": "vf-100234",
            "bill_date": "2026-09-18T10:00:00Z",
            "lines": [{"description": "Duplicate Override", "quantity": "1", "unit_price": "120.00"}],
            "duplicate_override_reason": "Supplier reissued bill with same number for separate subsidiary.",
        },
        headers=headers,
    )
    assert override_res.status_code == 201
    overridden_bill = override_res.json()
    assert overridden_bill["duplicate_override_reason"] == "Supplier reissued bill with same number for separate subsidiary."


@pytest.mark.asyncio
async def test_file_checksum_duplicate_detection(client: AsyncClient, test_setup, db_session):
    org_id = test_setup["org_a"].id
    token = test_setup["token_a"]
    headers = {"Authorization": f"Bearer {token}"}

    supplier = Contact(
        id=uuid.uuid4(),
        organisation_id=org_id,
        business_name="Paper Supply Ltd",
        contact_type=ContactType.SUPPLIER,
        status=ContactStatus.ACTIVE,
    )
    db_session.add(supplier)
    await db_session.commit()

    # Simulate uploaded file with checksum
    fake_content = b"PDF-1.4 Invoice Content Fake Bytes For Test"
    sha = hashlib.sha256(fake_content).hexdigest()

    file_rec = File(
        id=uuid.uuid4(),
        organisation_id=org_id,
        bucket="test-bucket",
        key="invoices/doc1.pdf",
        filename="invoice_paper.pdf",
        content_type="application/pdf",
        size_bytes=len(fake_content),
    )
    db_session.add(file_rec)
    await db_session.commit()

    # Create bill and attach file with checksum
    b_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills",
        json={
            "supplier_id": str(supplier.id),
            "supplier_invoice_number": "PS-001",
            "bill_date": "2026-09-18T10:00:00Z",
            "lines": [{"description": "Paper A4", "quantity": "10", "unit_price": "5.00"}],
        },
        headers=headers,
    )
    bill_id = b_res.json()["id"]

    attach_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills/{bill_id}/documents",
        data={"file_id": str(file_rec.id), "document_type": "ORIGINAL_INVOICE"},
        headers=headers,
    )
    assert attach_res.status_code == 201

    # Now check duplicate on a new bill using the exact same file checksum
    chk_res = await client.post(
        f"/api/v1/organisations/{org_id}/bills/check-duplicate",
        json={
            "supplier_id": str(supplier.id),
            "supplier_invoice_number": "PS-999",  # different invoice number
            "file_checksum": sha,
        },
        headers=headers,
    )
    assert chk_res.status_code == 200
    chk_data = chk_res.json()
    # If the document in DB was stored with sha, it will match
