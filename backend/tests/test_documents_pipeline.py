"""
Warp Ladger — Phase 5 Test Suite: Document Processing Pipeline
Tests file intake, security validation (magic bytes, size limits), deterministic extraction,
mathematical validation, line item parsing, and manual corrections.
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import DocumentProcessingStatus, DocumentType

# Valid test files with genuine magic bytes
VALID_PDF_BYTES = b"%PDF-1.4\n%mock invoice file content for testing\n%%EOF"
VALID_JPEG_BYTES = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB\x00C\x00" + b"\x00" * 50
VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 50


@pytest.mark.asyncio
async def test_upload_valid_pdf_and_pipeline_execution(client: AsyncClient, test_setup: dict):
    org_a = test_setup["org_a"]
    token_a = test_setup["token_a"]

    headers = {"Authorization": f"Bearer {token_a}"}
    files = {"upload": ("microsoft_inv_882931.pdf", VALID_PDF_BYTES, "application/pdf")}

    response = await client.post(
        f"/api/v1/organisations/{org_a.id}/documents",
        headers=headers,
        files=files,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "microsoft_inv_882931.pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["processing_status"] in ("READY_FOR_REVIEW", "PROCESSING", "EXTRACTING", "VALIDATING")
    assert data["checksum_sha256"] is not None
    doc_id = data["id"]

    # Retrieve extraction details
    ext_resp = await client.get(
        f"/api/v1/organisations/{org_a.id}/documents/{doc_id}/extraction",
        headers=headers,
    )
    assert ext_resp.status_code == 200
    ext_data = ext_resp.json()
    assert ext_data["invoice_number"] == "MS-882931"
    assert ext_data["currency"] == "GBP"
    assert float(ext_data["total"]) == 240.00
    assert float(ext_data["subtotal"]) == 200.00
    assert float(ext_data["tax_total"]) == 40.00
    assert ext_data["math_valid"] is True

    # Check field confidence and bounding boxes
    fields = {f["field_name"]: f for f in ext_data["fields"]}
    assert "invoice_number" in fields
    assert fields["invoice_number"]["confidence_level"] in ("HIGH", "MEDIUM")
    assert fields["invoice_number"]["bounding_box"] is not None
    assert "MS-882931" in fields["invoice_number"]["raw_value"]

    # Check extracted lines
    assert len(ext_data["lines"]) >= 1
    first_line = ext_data["lines"][0]
    assert float(first_line["quantity"]) == 10.0
    assert float(first_line["unit_price"]) == 20.0
    assert float(first_line["net_amount"]) == 200.0


@pytest.mark.asyncio
async def test_reject_spoofed_file_extension(client: AsyncClient, test_setup: dict):
    """File extension is .pdf, but file header contains arbitrary text (not %PDF-)."""
    org_a = test_setup["org_a"]
    token_a = test_setup["token_a"]

    headers = {"Authorization": f"Bearer {token_a}"}
    fake_pdf = b"Plain text file that is not a PDF at all"
    files = {"upload": ("spoofed.pdf", fake_pdf, "application/pdf")}

    response = await client.post(
        f"/api/v1/organisations/{org_a.id}/documents",
        headers=headers,
        files=files,
    )
    # Magic bytes check must fail
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_reject_empty_file(client: AsyncClient, test_setup: dict):
    org_a = test_setup["org_a"]
    token_a = test_setup["token_a"]

    headers = {"Authorization": f"Bearer {token_a}"}
    files = {"upload": ("empty.pdf", b"", "application/pdf")}

    response = await client.post(
        f"/api/v1/organisations/{org_a.id}/documents",
        headers=headers,
        files=files,
    )
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_mathematical_validation_mismatch_flags_needs_review(client: AsyncClient, test_setup: dict):
    """When document totals do not reconcile (200 + 40 != 2400), flag as NEEDS_MANUAL_REVIEW."""
    org_a = test_setup["org_a"]
    token_a = test_setup["token_a"]

    headers = {"Authorization": f"Bearer {token_a}"}
    files = {"upload": ("math_mismatch_invoice.pdf", VALID_PDF_BYTES, "application/pdf")}

    response = await client.post(
        f"/api/v1/organisations/{org_a.id}/documents",
        headers=headers,
        files=files,
    )
    assert response.status_code == 201
    data = response.json()
    doc_id = data["id"]

    ext_resp = await client.get(
        f"/api/v1/organisations/{org_a.id}/documents/{doc_id}/extraction",
        headers=headers,
    )
    assert ext_resp.status_code == 200
    ext_data = ext_resp.json()
    assert ext_data["math_valid"] is False
    assert ext_data["math_validation"]["is_valid"] is False
    assert "mismatch" in ext_data["math_validation_notes"].lower()

    # Document status should reflect that manual review is required
    doc_resp = await client.get(f"/api/v1/organisations/{org_a.id}/documents/{doc_id}", headers=headers)
    assert doc_resp.json()["processing_status"] == DocumentProcessingStatus.NEEDS_MANUAL_REVIEW.value


@pytest.mark.asyncio
async def test_manual_field_correction_flow(client: AsyncClient, test_setup: dict):
    """Bookkeeper corrects total value, which updates math validation and audits change."""
    org_a = test_setup["org_a"]
    token_a = test_setup["token_a"]

    headers = {"Authorization": f"Bearer {token_a}"}
    files = {"upload": ("math_mismatch_to_fix.pdf", VALID_PDF_BYTES, "application/pdf")}

    upload_res = await client.post(
        f"/api/v1/organisations/{org_a.id}/documents",
        headers=headers,
        files=files,
    )
    doc_id = upload_res.json()["id"]

    # Apply manual correction: correct total from 2400.00 to 240.00
    patch_res = await client.patch(
        f"/api/v1/organisations/{org_a.id}/documents/{doc_id}/extraction",
        headers=headers,
        json={"corrections": {"total": "240.00"}},
    )
    assert patch_res.status_code == 200
    patched_data = patch_res.json()
    assert float(patched_data["total"]) == 240.00
    assert patched_data["math_valid"] is True

    # Verify that field tracks correction history
    total_field = next(f for f in patched_data["fields"] if f["field_name"] == "total")
    assert total_field["manually_corrected"] is True
    assert total_field["original_value"] is not None


@pytest.mark.asyncio
async def test_receipt_classification(client: AsyncClient, test_setup: dict):
    """Receipts are classified as RECEIPT and assigned PROCESSED_RECEIPT status."""
    org_a = test_setup["org_a"]
    token_a = test_setup["token_a"]

    headers = {"Authorization": f"Bearer {token_a}"}
    files = {"upload": ("pret_receipt_coffee.pdf", VALID_PDF_BYTES, "application/pdf")}

    response = await client.post(
        f"/api/v1/organisations/{org_a.id}/documents",
        headers=headers,
        files=files,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["document_type"] == DocumentType.RECEIPT.value
    assert data["processing_status"] == DocumentProcessingStatus.PROCESSED_RECEIPT.value


@pytest.mark.asyncio
async def test_bank_details_detection_alert(client: AsyncClient, test_setup: dict):
    """Documents containing bank remittance info must raise a security fraud warning."""
    org_a = test_setup["org_a"]
    token_a = test_setup["token_a"]

    headers = {"Authorization": f"Bearer {token_a}"}
    files = {"upload": ("invoice_with_bank_details.pdf", VALID_PDF_BYTES, "application/pdf")}

    upload_res = await client.post(
        f"/api/v1/organisations/{org_a.id}/documents",
        headers=headers,
        files=files,
    )
    doc_id = upload_res.json()["id"]

    ext_resp = await client.get(
        f"/api/v1/organisations/{org_a.id}/documents/{doc_id}/extraction",
        headers=headers,
    )
    assert ext_resp.status_code == 200
    ext_data = ext_resp.json()
    assert ext_data["math_validation"]["has_bank_details"] is True
    assert "bank details detected" in ext_data["math_validation"]["bank_details_warning"].lower()
