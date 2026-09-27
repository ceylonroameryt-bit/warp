"""
Warp Ladger — Phase 5 Test Suite: Supplier Matching Engine
Verifies VAT matching, company number matching, email domain matching,
fuzzy name similarity, and strict multi-tenant isolation.
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Contact, ContactType
from app.documents.services.matching_service import SupplierMatchingService


@pytest.mark.asyncio
async def test_supplier_vat_exact_match(db_session: AsyncSession, test_setup: dict):
    org_a = test_setup["org_a"]

    # Create supplier in Org A
    supplier = Contact(
        organisation_id=org_a.id,
        contact_type=ContactType.SUPPLIER,
        business_name="Microsoft UK Headquarters",
        vat_number="GB724594615",
    )
    db_session.add(supplier)
    await db_session.flush()

    match_result = await SupplierMatchingService.match_supplier(
        db=db_session,
        org_id=org_a.id,
        extracted_name="Different Name Stated On Invoice",
        extracted_vat="GB 724 594 615",  # Space variations
    )

    assert match_result.matched_supplier_id == supplier.id
    assert match_result.is_exact_match is True
    assert float(match_result.confidence) == 1.00
    assert "VAT" in match_result.match_reason


@pytest.mark.asyncio
async def test_supplier_company_number_exact_match(db_session: AsyncSession, test_setup: dict):
    org_a = test_setup["org_a"]

    supplier = Contact(
        organisation_id=org_a.id,
        contact_type=ContactType.SUPPLIER,
        business_name="Acme Technology Limited",
        company_number="01624297",
    )
    db_session.add(supplier)
    await db_session.flush()

    match_result = await SupplierMatchingService.match_supplier(
        db=db_session,
        org_id=org_a.id,
        extracted_name="Acme Tech",
        extracted_company_number="01624297",
    )

    assert match_result.matched_supplier_id == supplier.id
    assert match_result.is_exact_match is True
    assert "company registration" in match_result.match_reason.lower()


@pytest.mark.asyncio
async def test_supplier_email_domain_match(db_session: AsyncSession, test_setup: dict):
    org_a = test_setup["org_a"]

    supplier = Contact(
        organisation_id=org_a.id,
        contact_type=ContactType.SUPPLIER,
        business_name="Cloud Hosting Co",
        email="accounts@fastcloudservers.co.uk",
    )
    db_session.add(supplier)
    await db_session.flush()

    match_result = await SupplierMatchingService.match_supplier(
        db=db_session,
        org_id=org_a.id,
        extracted_name="Fast Cloud",
        extracted_email="billing-noreply@fastcloudservers.co.uk",
    )

    assert match_result.matched_supplier_id == supplier.id
    assert "domain match" in match_result.match_reason.lower()


@pytest.mark.asyncio
async def test_supplier_fuzzy_name_match(db_session: AsyncSession, test_setup: dict):
    org_a = test_setup["org_a"]

    # In database: "Microsoft Limited"
    supplier = Contact(
        organisation_id=org_a.id,
        contact_type=ContactType.SUPPLIER,
        business_name="Microsoft Limited",
    )
    db_session.add(supplier)
    await db_session.flush()

    # Invoice extracted name: "Microsoft Ltd"
    match_result = await SupplierMatchingService.match_supplier(
        db=db_session,
        org_id=org_a.id,
        extracted_name="Microsoft Ltd",
    )

    assert match_result.matched_supplier_id == supplier.id
    assert float(match_result.confidence) >= 0.85


@pytest.mark.asyncio
async def test_supplier_matching_strict_tenant_isolation(db_session: AsyncSession, test_setup: dict):
    """
    Supplier exists in Org B with VAT GB724594615.
    Matching an invoice in Org A with that VAT must NEVER match Org B's supplier!
    """
    org_a = test_setup["org_a"]
    org_b = test_setup["org_b"]

    # Create supplier in Org B only
    supplier_b = Contact(
        organisation_id=org_b.id,
        contact_type=ContactType.SUPPLIER,
        business_name="Microsoft Corporation OrgB",
        vat_number="GB724594615",
    )
    db_session.add(supplier_b)
    await db_session.flush()

    # Match in Org A
    match_result = await SupplierMatchingService.match_supplier(
        db=db_session,
        org_id=org_a.id,
        extracted_name="Microsoft Corporation",
        extracted_vat="GB724594615",
    )

    # Must NOT match supplier_b!
    assert match_result.matched_supplier_id is None
    assert match_result.is_exact_match is False
