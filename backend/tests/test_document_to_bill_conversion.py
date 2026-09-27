"""
Warp Ladger — Phase 5 Test Suite: Document to Phase 4 Draft Bill Conversion
Verifies conversion to draft bill, source traceability, file attachment, idempotency,
and inline new supplier creation.
"""
import uuid
import pytest
from httpx import AsyncClient

from app.database.models import Contact, ContactType, DocumentProcessingStatus

VALID_PDF_BYTES = b"%PDF-1.4\n%bill conversion test PDF content\n%%EOF"


@pytest.mark.asyncio
async def test_convert_extraction_to_draft_bill_end_to_end(client: AsyncClient, test_setup: dict):
    org_a = test_setup["org_a"]
    token_a = test_setup["token_a"]
    headers = {"Authorization": f"Bearer {token_a}"}

    # 1. Create existing supplier in Org A
    supp_resp = await client.post(
        f"/api/v1/organisations/{org_a.id}/contacts",
        headers=headers,
        json={
            "contact_type": "SUPPLIER",
            "business_name": "Microsoft Limited",
            "vat_number": "GB724594615",
            "email": "invoices@microsoft.com",
        },
    )
    assert supp_resp.status_code == 201
    supplier_id = supp_resp.json()["id"]

    # 2. Upload document (will extract and match supplier)
    files = {"upload": ("microsoft_invoice_march.pdf", VALID_PDF_BYTES, "application/pdf")}
    upload_res = await client.post(
        f"/api/v1/organisations/{org_a.id}/documents",
        headers=headers,
        files=files,
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 3. Convert extraction to Phase 4 Draft Bill
    conv_res = await client.post(
        f"/api/v1/organisations/{org_a.id}/documents/{doc_id}/create-bill",
        headers=headers,
        json={"supplier_id": supplier_id},
    )
    assert conv_res.status_code == 201
    bill_data = conv_res.json()

    assert bill_data["status"] == "DRAFT"
    assert bill_data["supplier_invoice_number"] == "MS-882931"
    assert float(bill_data["total"]) == 240.00
    assert bill_data["internal_bill_number"] is not None
    assert bill_data["source_document_id"] == doc_id
    assert len(bill_data["documents"]) >= 1
    assert bill_data["documents"][0]["document_type"] == "ORIGINAL_INVOICE"

    # 4. Verify CapturedDocument status updated
    doc_check = await client.get(f"/api/v1/organisations/{org_a.id}/documents/{doc_id}", headers=headers)
    assert doc_check.json()["processing_status"] == DocumentProcessingStatus.CONVERTED_TO_BILL.value
    assert doc_check.json()["created_bill_id"] == bill_data["id"]

    # 5. Idempotency test: second conversion call returns the SAME bill!
    conv_res2 = await client.post(
        f"/api/v1/organisations/{org_a.id}/documents/{doc_id}/create-bill",
        headers=headers,
        json={"supplier_id": supplier_id},
    )
    assert conv_res2.status_code in (200, 201)
    assert conv_res2.json()["id"] == bill_data["id"]


@pytest.mark.asyncio
async def test_convert_to_bill_with_inline_new_supplier_creation(client: AsyncClient, test_setup: dict):
    org_a = test_setup["org_a"]
    token_a = test_setup["token_a"]
    headers = {"Authorization": f"Bearer {token_a}"}

    files = {"upload": ("new_vendor_bill.pdf", VALID_PDF_BYTES, "application/pdf")}
    upload_res = await client.post(
        f"/api/v1/organisations/{org_a.id}/documents",
        headers=headers,
        files=files,
    )
    doc_id = upload_res.json()["id"]

    # Convert requesting new supplier creation
    conv_res = await client.post(
        f"/api/v1/organisations/{org_a.id}/documents/{doc_id}/create-bill",
        headers=headers,
        json={
            "create_new_supplier": True,
            "new_supplier_name": "Apex Hosting & Cloud Ltd",
        },
    )
    assert conv_res.status_code == 201
    bill_data = conv_res.json()
    assert bill_data["status"] == "DRAFT"
    assert bill_data["supplier_id"] is not None

    # Check newly created supplier in contacts
    new_supp_id = bill_data["supplier_id"]
    contact_res = await client.get(
        f"/api/v1/organisations/{org_a.id}/contacts/{new_supp_id}",
        headers=headers,
    )
    assert contact_res.status_code == 200
    assert contact_res.json()["business_name"] == "Apex Hosting & Cloud Ltd"
    assert contact_res.json()["contact_type"] == "SUPPLIER"
