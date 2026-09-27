"""
Warp Ladger — Phase 5 Test Suite: Duplicate Document Protection
Tests Layer 1 (exact file SHA-256), Layer 2 (supplier + invoice number),
Layer 3 (fuzzy date + total), and duplicate override.
"""
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.bills.duplicate_service import normalize_invoice_number
from app.database.models import Bill, BillStatus, Contact, ContactType, DocumentProcessingStatus
from app.documents.services.duplicate_service import DocumentDuplicateService

VALID_PDF_BYTES = b"%PDF-1.4\n%unique duplicate test file content\n%%EOF"


@pytest.mark.asyncio
async def test_layer1_exact_file_duplicate_detection(client: AsyncClient, test_setup: dict):
    org_a = test_setup["org_a"]
    token_a = test_setup["token_a"]

    headers = {"Authorization": f"Bearer {token_a}"}
    files = {"upload": ("invoice_run_1.pdf", VALID_PDF_BYTES, "application/pdf")}

    # First upload
    res1 = await client.post(
        f"/api/v1/organisations/{org_a.id}/documents",
        headers=headers,
        files=files,
    )
    assert res1.status_code == 201
    doc1_id = res1.json()["id"]

    # Second upload with identical bytes
    files2 = {"upload": ("invoice_run_copy.pdf", VALID_PDF_BYTES, "application/pdf")}
    res2 = await client.post(
        f"/api/v1/organisations/{org_a.id}/documents",
        headers=headers,
        files=files2,
    )
    assert res2.status_code == 201
    doc2_data = res2.json()

    # Second document should be flagged as DUPLICATE_FILE
    assert doc2_data["processing_status"] == DocumentProcessingStatus.DUPLICATE_FILE.value
    assert doc2_data["checksum_sha256"] == res1.json()["checksum_sha256"]


@pytest.mark.asyncio
async def test_layer2_supplier_invoice_number_duplicate(db_session: AsyncSession, test_setup: dict):
    org_a = test_setup["org_a"]

    # Create supplier and existing bill in database
    supplier = Contact(
        organisation_id=org_a.id,
        contact_type=ContactType.SUPPLIER,
        business_name="Microsoft Limited",
    )
    db_session.add(supplier)
    await db_session.flush()

    existing_bill = Bill(
        organisation_id=org_a.id,
        supplier_id=supplier.id,
        supplier_invoice_number="MS-882931",
        supplier_invoice_number_normalized=normalize_invoice_number("MS-882931"),
        internal_bill_number="BILL-000100",
        status=BillStatus.AWAITING_PAYMENT,
        bill_date=datetime.now(UTC),
        due_date=datetime.now(UTC) + timedelta(days=30),
        currency="GBP",
        subtotal=Decimal("200.00"),
        discount_total=Decimal("0.00"),
        tax_total=Decimal("40.00"),
        total=Decimal("240.00"),
        amount_paid=Decimal("0.00"),
        amount_due=Decimal("240.00"),
    )
    db_session.add(existing_bill)
    await db_session.flush()

    # Check duplicate for a new document extracting MS-882931
    dup_res = await DocumentDuplicateService.check_duplicates(
        db=db_session,
        org_id=org_a.id,
        doc_id=uuid.uuid4(),
        checksum_sha256="different_sha256_hash",
        supplier_id=supplier.id,
        invoice_number="MS-882931",
    )

    assert dup_res.is_duplicate is True
    assert dup_res.severity == "BLOCK"
    assert dup_res.duplicate_bill_id == existing_bill.id
    assert "already exists" in dup_res.reason.lower()


@pytest.mark.asyncio
async def test_layer3_fuzzy_duplicate_detection(db_session: AsyncSession, test_setup: dict):
    org_a = test_setup["org_a"]

    supplier = Contact(
        organisation_id=org_a.id,
        contact_type=ContactType.SUPPLIER,
        business_name="Telecom Supplies UK",
    )
    db_session.add(supplier)
    await db_session.flush()

    bill_date = datetime.now(UTC)
    existing_bill = Bill(
        organisation_id=org_a.id,
        supplier_id=supplier.id,
        supplier_invoice_number="TEL-1001",
        supplier_invoice_number_normalized="TEL1001",
        internal_bill_number="BILL-000200",
        status=BillStatus.DRAFT,
        bill_date=bill_date,
        due_date=bill_date + timedelta(days=14),
        currency="GBP",
        subtotal=Decimal("150.00"),
        discount_total=Decimal("0.00"),
        tax_total=Decimal("30.00"),
        total=Decimal("180.00"),
        amount_paid=Decimal("0.00"),
        amount_due=Decimal("180.00"),
    )
    db_session.add(existing_bill)
    await db_session.flush()

    # Check fuzzy duplicate: different invoice number (TEL-1002), but same supplier, total (180.00), and 1 day apart
    dup_res = await DocumentDuplicateService.check_duplicates(
        db=db_session,
        org_id=org_a.id,
        doc_id=uuid.uuid4(),
        checksum_sha256="different_checksum_hash_2",
        supplier_id=supplier.id,
        invoice_number="TEL-1002",
        invoice_date=bill_date + timedelta(days=1),
        total=Decimal("180.00"),
    )

    assert dup_res.is_duplicate is True
    assert dup_res.severity == "WARN"
    assert dup_res.duplicate_bill_id == existing_bill.id


@pytest.mark.asyncio
async def test_duplicate_override_flow(client: AsyncClient, test_setup: dict):
    """Authorized user can override duplicate file status with justification reason."""
    org_a = test_setup["org_a"]
    token_a = test_setup["token_a"]

    headers = {"Authorization": f"Bearer {token_a}"}
    files = {"upload": ("dup1.pdf", VALID_PDF_BYTES, "application/pdf")}
    await client.post(f"/api/v1/organisations/{org_a.id}/documents", headers=headers, files=files)

    # Second upload is marked DUPLICATE_FILE
    files2 = {"upload": ("dup2.pdf", VALID_PDF_BYTES, "application/pdf")}
    res2 = await client.post(f"/api/v1/organisations/{org_a.id}/documents", headers=headers, files=files2)
    doc2_id = res2.json()["id"]
    assert res2.json()["processing_status"] == DocumentProcessingStatus.DUPLICATE_FILE.value

    # Override duplicate
    override_res = await client.post(
        f"/api/v1/organisations/{org_a.id}/documents/{doc2_id}/override-duplicate",
        headers=headers,
        json={"reason": "Customer re-issued invoice with different internal reference"},
    )
    assert override_res.status_code == 200
    assert override_res.json()["processing_status"] == DocumentProcessingStatus.READY_FOR_REVIEW.value
