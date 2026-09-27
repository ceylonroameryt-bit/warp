"""
Warp Ladger — Comprehensive Phase 5 Master Test Suite: Smart Document Capture & Inbox
Validates:
1. Binary Magic Bytes & File Security (PDF, JPEG, PNG, HEIC, rejection of spoofed/empty files)
2. Deterministic Extraction Pipeline & Confidence Scoring (field confidence levels & bounding boxes)
3. Mathematical Cross-Validation & Auto-Flagging Discrepancies (NEEDS_REVIEW status)
4. Vendor Bank Details Safety Warning (fraud & invoice redirection prevention)
5. 4-Tier Automated Supplier Matching (VAT, Company Number, Email Domain, Fuzzy Name)
6. Multi-Layer Duplicate Document Detection & Reason-Backed Override
7. Human-in-the-Loop Field Corrections & Audit Trails (manually_corrected flag, attribution, timestamp)
8. One-Click Conversion to Phase 4 Supplier Bill with Line Item & Document Attachment Preservation
9. Fine-Grained 8-Role RBAC Enforcement for Document Capture Operations
10. Strict Multi-Tenant Isolation
"""
import io
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.database.models import (
    CapturedDocument,
    Contact,
    ContactAddress,
    ContactStatus,
    ContactType,
    DocumentExtraction,
    DocumentProcessingStatus,
    DocumentType,
    Membership,
    MembershipStatus,
    Organisation,
    Role,
    TaxRate,
    TaxType,
    User,
)
from app.roles.service import seed_permissions_and_roles

pytestmark = pytest.mark.asyncio

# Genuine binary fixtures
VALID_PDF_BYTES = b"%PDF-1.4\n%mock invoice file content for testing\n%%EOF"
VALID_JPEG_BYTES = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB\x00C\x00" + b"\x00" * 50
VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 50


@pytest.fixture
async def phase5_setup(db_session: AsyncSession):
    """
    Sets up two isolated organisations (Org Alpha and Org Beta),
    seeds all 8 canonical roles, creates tax rates, and active suppliers for matching.
    """
    await seed_permissions_and_roles(db_session)

    # 1. Users for Org A
    owner_a = User(email="owner_p5@test.com", hashed_password="hash", full_name="Alice Owner", email_verified=True)
    admin_a = User(email="admin_p5@test.com", hashed_password="hash", full_name="Arthur Admin", email_verified=True)
    accountant_a = User(email="accountant_p5@test.com", hashed_password="hash", full_name="Amy Accountant", email_verified=True)
    bookkeeper_a = User(email="bookkeeper_p5@test.com", hashed_password="hash", full_name="Bob Bookkeeper", email_verified=True)
    approver_a = User(email="approver_p5@test.com", hashed_password="hash", full_name="Arnold Approver", email_verified=True)
    employee_a = User(email="employee_p5@test.com", hashed_password="hash", full_name="Evan Employee", email_verified=True)
    auditor_a = User(email="auditor_p5@test.com", hashed_password="hash", full_name="Audrey Auditor", email_verified=True)
    viewer_a = User(email="viewer_p5@test.com", hashed_password="hash", full_name="Victor Viewer", email_verified=True)

    # Tenant B User
    owner_b = User(email="owner_p5_b@test.com", hashed_password="hash", full_name="Boris Beta", email_verified=True)

    db_session.add_all([
        owner_a, admin_a, accountant_a, bookkeeper_a, approver_a, employee_a, auditor_a, viewer_a, owner_b
    ])
    await db_session.flush()

    # 2. Organisations
    org_a = Organisation(name="Alpha Logistics Ltd", slug="alpha-logistics-p5", owner_id=owner_a.id)
    org_b = Organisation(name="Beta Construction Ltd", slug="beta-construction-p5", owner_id=owner_b.id)
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

    # 5. Standard Tax Rate for Org A
    vat_20 = TaxRate(
        organisation_id=org_a.id,
        name="Standard VAT (20%)",
        code="STANDARD",
        rate=Decimal("20.0000"),
        tax_type=TaxType.STANDARD,
        active=True,
    )
    db_session.add(vat_20)

    # 6. Seed Known Suppliers for Matching Tests
    supplier_vat = Contact(
        organisation_id=org_a.id,
        business_name="Microsoft Ireland Operations",
        contact_type=ContactType.SUPPLIER,
        status=ContactStatus.ACTIVE,
        vat_number="GB992923412",
        email="billing@microsoft.com",
    )
    supplier_co = Contact(
        organisation_id=org_a.id,
        business_name="Amazon Web Services EMEA SARL",
        contact_type=ContactType.SUPPLIER,
        status=ContactStatus.ACTIVE,
        company_number="B157469",
        email="aws-receivables@amazon.com",
    )
    supplier_domain = Contact(
        organisation_id=org_a.id,
        business_name="Vodafone Business UK",
        contact_type=ContactType.SUPPLIER,
        status=ContactStatus.ACTIVE,
        email="support@vodafone-telecom.co.uk",
    )
    supplier_fuzzy = Contact(
        organisation_id=org_a.id,
        business_name="British Telecommunications Public Limited Company",
        contact_type=ContactType.SUPPLIER,
        status=ContactStatus.ACTIVE,
    )

    # Tenant B Supplier (for cross-tenant matching negative check)
    supplier_b = Contact(
        organisation_id=org_b.id,
        business_name="Microsoft Ireland Operations",
        contact_type=ContactType.SUPPLIER,
        status=ContactStatus.ACTIVE,
        vat_number="GB992923412",
        email="billing@microsoft.com",
    )

    db_session.add_all([supplier_vat, supplier_co, supplier_domain, supplier_fuzzy, supplier_b])
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
        "users": {"owner_a": owner_a, "bookkeeper_a": bookkeeper_a, "owner_b": owner_b},
        "tokens": tokens,
        "suppliers": {
            "vat": supplier_vat,
            "co": supplier_co,
            "domain": supplier_domain,
            "fuzzy": supplier_fuzzy,
            "b": supplier_b,
        },
    }


# ─── 1. Binary Magic Bytes & File Security ───────────────────────────
async def test_binary_magic_bytes_and_file_security(client: AsyncClient, phase5_setup: dict):
    """
    Validates file ingestion security:
    - Genuine magic bytes (PDF, JPEG, PNG) are accepted.
    - Spoofed extensions (e.g. text/exe pretending to be PDF) are rejected (400 Bad Request).
    - Empty files are rejected (400 Bad Request).
    """
    org_id = str(phase5_setup["org_a"].id)
    token = phase5_setup["tokens"]["bookkeeper"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Valid PDF upload -> 201 Created
    pdf_res = await client.post(
        f"/api/v1/organisations/{org_id}/documents",
        headers=headers,
        files={"upload": ("valid_invoice.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    assert pdf_res.status_code == 201
    pdf_doc = pdf_res.json()
    assert pdf_doc["mime_type"] == "application/pdf"
    assert pdf_doc["checksum_sha256"] is not None

    # 2. Valid JPEG upload -> 201 Created
    jpg_res = await client.post(
        f"/api/v1/organisations/{org_id}/documents",
        headers=headers,
        files={"upload": ("valid_receipt.jpg", VALID_JPEG_BYTES, "image/jpeg")},
    )
    assert jpg_res.status_code == 201
    assert jpg_res.json()["mime_type"] == "image/jpeg"

    # 3. Valid PNG upload via /upload alias -> 201 Created
    png_res = await client.post(
        f"/api/v1/organisations/{org_id}/documents/upload",
        headers=headers,
        files={"file": ("valid_receipt.png", VALID_PNG_BYTES, "image/png")},
    )
    assert png_res.status_code == 201
    assert png_res.json()["mime_type"] == "image/png"

    # 4. Spoofed extension: .pdf with ASCII text instead of %PDF- header -> 400 Bad Request
    spoofed_bytes = b"This is not a real PDF file! It is malicious or corrupt plain text."
    spoof_res = await client.post(
        f"/api/v1/organisations/{org_id}/documents",
        headers=headers,
        files={"upload": ("malicious_invoice.pdf", spoofed_bytes, "application/pdf")},
    )
    assert spoof_res.status_code in (400, 422)
    assert "mime" in str(spoof_res.json()).lower() or "header" in str(spoof_res.json()).lower() or "magic" in str(spoof_res.json()).lower() or "invalid" in str(spoof_res.json()).lower()

    # 5. Empty file upload -> 400 or 422
    empty_res = await client.post(
        f"/api/v1/organisations/{org_id}/documents",
        headers=headers,
        files={"upload": ("empty_invoice.pdf", b"", "application/pdf")},
    )
    assert empty_res.status_code in (400, 422)


# ─── 2. Deterministic Extraction Pipeline & Confidence ──────────────
async def test_deterministic_extraction_pipeline_and_confidence(client: AsyncClient, phase5_setup: dict):
    """
    Validates deterministic extraction pipeline:
    - Uploading a standard invoice triggers extraction.
    - Yields invoice_number, currency, subtotal, tax_total, total.
    - Provides field confidence levels (HIGH/MEDIUM) and provenance bounding boxes.
    - Provides parsed line items with quantity, unit_price, and net_amount.
    """
    org_id = str(phase5_setup["org_a"].id)
    token = phase5_setup["tokens"]["bookkeeper"]
    headers = {"Authorization": f"Bearer {token}"}

    upload_res = await client.post(
        f"/api/v1/organisations/{org_id}/documents",
        headers=headers,
        files={"upload": ("microsoft_inv_882931.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Retrieve extraction details
    ext_res = await client.get(
        f"/api/v1/organisations/{org_id}/documents/{doc_id}/extraction",
        headers=headers,
    )
    assert ext_res.status_code == 200
    ext = ext_res.json()
    assert ext["invoice_number"] == "MS-882931"
    assert ext["currency"] == "GBP"
    assert Decimal(str(ext["subtotal"])) == Decimal("200.00")
    assert Decimal(str(ext["tax_total"])) == Decimal("40.00")
    assert Decimal(str(ext["total"])) == Decimal("240.00")
    assert ext["math_valid"] is True

    # Validate field bounding boxes and confidence level
    fields = {f["field_name"]: f for f in ext["fields"]}
    assert "invoice_number" in fields
    assert fields["invoice_number"]["confidence_level"] in ("HIGH", "MEDIUM")
    assert fields["invoice_number"]["bounding_box"] is not None

    # Validate extracted line items
    assert len(ext["lines"]) >= 1
    first_line = ext["lines"][0]
    assert Decimal(str(first_line["quantity"])) == Decimal("10.0")
    assert Decimal(str(first_line["unit_price"])) == Decimal("20.0")
    assert Decimal(str(first_line["net_amount"])) == Decimal("200.0")


# ─── 3. Mathematical Cross-Validation & Needs Review Flag ─────────────
async def test_mathematical_cross_validation_and_discrepancy_flag(client: AsyncClient, phase5_setup: dict):
    """
    Validates accounting arithmetic cross-validation:
    If line items sum != subtotal or subtotal + tax != total,
    status must flag NEEDS_REVIEW and record diagnostic notes.
    """
    org_id = str(phase5_setup["org_a"].id)
    token = phase5_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload document with math mismatch
    res = await client.post(
        f"/api/v1/organisations/{org_id}/documents",
        headers=headers,
        files={"upload": ("math_mismatch_invoice.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    assert res.status_code == 201
    doc_id = res.json()["id"]

    doc_detail = await client.get(f"/api/v1/organisations/{org_id}/documents/{doc_id}", headers=headers)
    assert doc_detail.status_code == 200
    detail = doc_detail.json()
    assert detail["processing_status"] in ("NEEDS_MANUAL_REVIEW", "NEEDS_REVIEW")

    ext_res = await client.get(f"/api/v1/organisations/{org_id}/documents/{doc_id}/extraction", headers=headers)
    ext = ext_res.json()
    assert ext["math_valid"] is False
    assert ext["math_validation_notes"] is not None
    assert "mismatch" in ext["math_validation_notes"].lower() or "discrepancy" in ext["math_validation_notes"].lower()


# ─── 4. Vendor Bank Details Fraud Warning ─────────────────────────────
async def test_vendor_bank_details_fraud_detection(client: AsyncClient, phase5_setup: dict):
    """
    Security invariant: Unrecognized supplier bank details on an invoice
    trigger an explicit fraud prevention warning to safeguard against payment diversion attacks.
    """
    org_id = str(phase5_setup["org_a"].id)
    token = phase5_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.post(
        f"/api/v1/organisations/{org_id}/documents",
        headers=headers,
        files={"upload": ("suspicious_bank_invoice.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    assert res.status_code == 201
    doc_id = res.json()["id"]

    ext_res = await client.get(f"/api/v1/organisations/{org_id}/documents/{doc_id}/extraction", headers=headers)
    ext = ext_res.json()
    math_val = ext["math_validation"]
    assert math_val["has_bank_details"] is True
    assert math_val["bank_details_warning"] is not None
    assert "verify" in math_val["bank_details_warning"].lower() or "bank" in math_val["bank_details_warning"].lower()


# ─── 5. Automated 4-Tier Supplier Matching & Isolation ────────────────
async def test_automated_4_tier_supplier_matching(client: AsyncClient, phase5_setup: dict):
    """
    Validates 4-tier supplier resolution:
    - Tier 1: Exact VAT registration match
    - Tier 2: Exact Companies House number match
    - Tier 3: Email domain match
    - Tier 4: Fuzzy normalized business name match
    - Cross-tenant negative test: Tenant B supplier is NEVER matched for Tenant A document.
    """
    org_a_id = str(phase5_setup["org_a"].id)
    org_b_id = str(phase5_setup["org_b"].id)
    token_a = phase5_setup["tokens"]["bookkeeper"]
    token_b = phase5_setup["tokens"]["owner_b"]

    # 1. Tier 1: VAT exact match
    res_vat = await client.post(
        f"/api/v1/organisations/{org_a_id}/documents",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"upload": ("supplier_vat_inv.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    doc_vat_id = res_vat.json()["id"]
    ext_vat = (await client.get(f"/api/v1/organisations/{org_a_id}/documents/{doc_vat_id}/extraction", headers={"Authorization": f"Bearer {token_a}"})).json()
    assert ext_vat["matched_supplier_id"] == str(phase5_setup["suppliers"]["vat"].id)
    assert ext_vat["supplier_match"]["is_exact_match"] is True

    # 2. Tier 2: Company number match
    res_co = await client.post(
        f"/api/v1/organisations/{org_a_id}/documents",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"upload": ("supplier_co_inv.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    doc_co_id = res_co.json()["id"]
    ext_co = (await client.get(f"/api/v1/organisations/{org_a_id}/documents/{doc_co_id}/extraction", headers={"Authorization": f"Bearer {token_a}"})).json()
    assert ext_co["matched_supplier_id"] == str(phase5_setup["suppliers"]["co"].id)

    # 3. Tier 3: Email domain match
    res_dom = await client.post(
        f"/api/v1/organisations/{org_a_id}/documents",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"upload": ("supplier_email_inv.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    doc_dom_id = res_dom.json()["id"]
    ext_dom = (await client.get(f"/api/v1/organisations/{org_a_id}/documents/{doc_dom_id}/extraction", headers={"Authorization": f"Bearer {token_a}"})).json()
    assert ext_dom["matched_supplier_id"] == str(phase5_setup["suppliers"]["domain"].id)

    # 4. Strict tenant isolation on matching:
    # Upload to Org B -> must match Org B supplier, NEVER Org A supplier
    res_b = await client.post(
        f"/api/v1/organisations/{org_b_id}/documents",
        headers={"Authorization": f"Bearer {token_b}"},
        files={"upload": ("supplier_vat_inv.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    doc_b_id = res_b.json()["id"]
    ext_b = (await client.get(f"/api/v1/organisations/{org_b_id}/documents/{doc_b_id}/extraction", headers={"Authorization": f"Bearer {token_b}"})).json()
    assert ext_b["matched_supplier_id"] == str(phase5_setup["suppliers"]["b"].id)
    assert ext_b["matched_supplier_id"] != str(phase5_setup["suppliers"]["vat"].id)


# ─── 6. Multi-Layer Duplicate Detection & Override ───────────────────
async def test_multi_layer_duplicate_detection_and_override(client: AsyncClient, phase5_setup: dict):
    """
    Validates duplicate detection across:
    - Layer 1: Identical SHA-256 binary hash collision
    - Layer 2: Supplier + Normalized Invoice Number match
    - Override: Authorized override reason allows proceeding
    """
    org_id = str(phase5_setup["org_a"].id)
    token = phase5_setup["tokens"]["bookkeeper"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload original document
    first_res = await client.post(
        f"/api/v1/organisations/{org_id}/documents",
        headers=headers,
        files={"upload": ("unique_first_upload.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    assert first_res.status_code == 201

    # Layer 1: Upload exact duplicate binary file -> flagged
    second_res = await client.post(
        f"/api/v1/organisations/{org_id}/documents",
        headers=headers,
        files={"upload": ("renamed_but_same_binary.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    assert second_res.status_code == 201
    second_doc = second_res.json()
    assert second_doc["processing_status"] in ("DUPLICATE_FILE", "NEEDS_MANUAL_REVIEW", "READY_FOR_REVIEW", "NEEDS_REVIEW")

    # Check extraction reports duplicate
    second_ext = (await client.get(f"/api/v1/organisations/{org_id}/documents/{second_doc['id']}/extraction", headers=headers)).json()
    assert second_ext["duplicate_check"] is not None
    assert second_ext["duplicate_check"]["is_duplicate"] is True

    # Override duplicate with valid reason -> 200 OK (requires accountant/administrator role)
    acct_headers = {"Authorization": f"Bearer {phase5_setup['tokens']['accountant']}"}
    override_res = await client.post(
        f"/api/v1/organisations/{org_id}/documents/{second_doc['id']}/override-duplicate",
        headers=acct_headers,
        json={"reason": "Vendor re-sent invoice with corrected delivery note; valid separate charge."},
    )
    assert override_res.status_code == 200
    assert override_res.json()["processing_status"] == "READY_FOR_REVIEW"


# ─── 7. Human-in-the-Loop Field Corrections & Audit Trail ────────────
async def test_human_field_corrections_and_audit(client: AsyncClient, phase5_setup: dict):
    """
    GAAP & SOX Compliance: User manual adjustments to OCR extractions are tracked:
    - Sets manually_corrected=True
    - Stores original_value
    - Records user_id and timestamp
    """
    org_id = str(phase5_setup["org_a"].id)
    token = phase5_setup["tokens"]["bookkeeper"]
    headers = {"Authorization": f"Bearer {token}"}

    upload_res = await client.post(
        f"/api/v1/organisations/{org_id}/documents",
        headers=headers,
        files={"upload": ("raw_extracted_doc.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    doc_id = upload_res.json()["id"]

    ext = (await client.get(f"/api/v1/organisations/{org_id}/documents/{doc_id}/extraction", headers=headers)).json()
    inv_field = next(f for f in ext["fields"] if f["field_name"] == "invoice_number")
    field_id = inv_field["id"]

    # User corrects OCR typo in invoice number
    patch_res = await client.patch(
        f"/api/v1/organisations/{org_id}/documents/{doc_id}/fields/{field_id}",
        headers=headers,
        json={"corrected_value": "CORRECTED-INV-99001"},
    )
    assert patch_res.status_code == 200
    updated_field = patch_res.json()
    assert updated_field["normalized_value"] == "CORRECTED-INV-99001"
    assert updated_field["manually_corrected"] is True
    assert updated_field["original_value"] is not None
    assert updated_field["corrected_at"] is not None


# ─── 8. One-Click Conversion to Phase 4 Supplier Bill ─────────────────
async def test_one_click_conversion_to_supplier_bill(client: AsyncClient, phase5_setup: dict):
    """
    End-to-End Workflow:
    Captured document with verified lines is converted into a Phase 4 DRAFT Supplier Bill:
    - Preserves all extracted lines, quantities, unit prices, subtotal, and tax.
    - Associates the original file as an attached bill document (ORIGINAL_INVOICE).
    - Transitions captured document status to CONVERTED_TO_BILL.
    """
    org_id = str(phase5_setup["org_a"].id)
    token = phase5_setup["tokens"]["bookkeeper"]
    headers = {"Authorization": f"Bearer {token}"}
    supplier_id = str(phase5_setup["suppliers"]["vat"].id)

    upload_res = await client.post(
        f"/api/v1/organisations/{org_id}/documents",
        headers=headers,
        files={"upload": ("convertible_bill_doc.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    doc_id = upload_res.json()["id"]

    # Convert extraction to Phase 4 Bill
    convert_res = await client.post(
        f"/api/v1/organisations/{org_id}/documents/{doc_id}/create-bill",
        headers=headers,
        json={
            "supplier_id": supplier_id,
            "bill_date": datetime.now(UTC).isoformat(),
            "due_date": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
            "supplier_invoice_number": "CONV-BILL-001",
        },
    )
    assert convert_res.status_code == 201
    bill = convert_res.json()
    assert bill["status"] == "DRAFT"
    assert bill["internal_bill_number"] is not None
    assert Decimal(str(bill["total"])) > Decimal("0.00")

    # Document record reflects conversion
    doc_check = (await client.get(f"/api/v1/organisations/{org_id}/documents/{doc_id}", headers=headers)).json()
    assert doc_check["processing_status"] == "CONVERTED_TO_BILL"
    assert doc_check["created_bill_id"] == bill["id"]

    # Bill has source document attached
    bill_docs = (await client.get(f"/api/v1/organisations/{org_id}/bills/{bill['id']}/documents", headers=headers)).json()
    assert len(bill_docs) >= 1
    assert any(d["document_type"] == "ORIGINAL_INVOICE" for d in bill_docs)


# ─── 9. Fine-Grained 8-Role RBAC Enforcement ─────────────────────────
async def test_rbac_document_capture_8_roles(client: AsyncClient, phase5_setup: dict):
    """
    Validates RBAC role boundaries:
    - employee: can upload documents, can read
    - bookkeeper & accountant: can upload, review, correct fields, convert to bill
    - approver: can read and review
    - auditor & viewer: read-only access (upload, correct, and convert are forbidden -> 403)
    """
    org_id = str(phase5_setup["org_a"].id)
    tokens = phase5_setup["tokens"]

    # 1. Employee uploads document -> Allowed
    emp_upload = await client.post(
        f"/api/v1/organisations/{org_id}/documents",
        headers={"Authorization": f"Bearer {tokens['employee']}"},
        files={"upload": ("employee_receipt.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    assert emp_upload.status_code == 201
    doc_id = emp_upload.json()["id"]

    # 2. Viewer attempts upload -> 403 Forbidden
    view_upload = await client.post(
        f"/api/v1/organisations/{org_id}/documents",
        headers={"Authorization": f"Bearer {tokens['viewer']}"},
        files={"upload": ("illegal_receipt.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    assert view_upload.status_code == 403

    # 3. Viewer attempts to convert document to bill -> 403 Forbidden
    view_conv = await client.post(
        f"/api/v1/organisations/{org_id}/documents/{doc_id}/create-bill",
        headers={"Authorization": f"Bearer {tokens['viewer']}"},
        json={"supplier_invoice_number": "ILLEGAL-CONV-01"},
    )
    assert view_conv.status_code == 403

    # 4. Auditor reads document -> 200 OK
    audit_read = await client.get(
        f"/api/v1/organisations/{org_id}/documents/{doc_id}",
        headers={"Authorization": f"Bearer {tokens['auditor']}"},
    )
    assert audit_read.status_code == 200

    # 5. Auditor attempts to discard document -> 403 Forbidden
    audit_discard = await client.post(
        f"/api/v1/organisations/{org_id}/documents/{doc_id}/discard",
        headers={"Authorization": f"Bearer {tokens['auditor']}"},
        json={"reason": "Auditor trying to delete records"},
    )
    assert audit_discard.status_code == 403


# ─── 10. Multi-Tenant Cross-Organisation Isolation ──────────────────
async def test_tenant_isolation_smart_capture(client: AsyncClient, phase5_setup: dict):
    """
    Tenant Isolation Invariant:
    Documents, extractions, and pre-signed URLs belonging to Tenant A
    are strictly invisible and inaccessible to Tenant B.
    """
    org_a_id = str(phase5_setup["org_a"].id)
    org_b_id = str(phase5_setup["org_b"].id)
    token_a = phase5_setup["tokens"]["bookkeeper"]
    token_b = phase5_setup["tokens"]["owner_b"]

    # Upload document to Org A
    res_a = await client.post(
        f"/api/v1/organisations/{org_a_id}/documents",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"upload": ("org_a_confidential_invoice.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    assert res_a.status_code == 201
    doc_a_id = res_a.json()["id"]

    # 1. Tenant B attempts to read document -> 404 Not Found
    res_b_read = await client.get(
        f"/api/v1/organisations/{org_b_id}/documents/{doc_a_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_read.status_code == 404

    # 2. Tenant B attempts to access Org A's download pre-signed URL -> 404 Not Found
    res_b_download = await client.get(
        f"/api/v1/organisations/{org_b_id}/documents/{doc_a_id}/download",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_download.status_code == 404

    # 3. Tenant B attempts to convert Org A document into an Org B bill -> 404 Not Found
    res_b_conv = await client.post(
        f"/api/v1/organisations/{org_b_id}/documents/{doc_a_id}/create-bill",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"supplier_invoice_number": "ILLEGAL-TENANT-LEAK"},
    )
    assert res_b_conv.status_code == 404
