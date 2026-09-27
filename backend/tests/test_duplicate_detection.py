"""
Warp Ladger — Duplicate Contact Detection & Normalization Tests
Section 28 & Section 57 Compliance.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_duplicate_vat_number_detection(client: AsyncClient, test_setup: dict):
    org_id = str(test_setup["org_a"].id)
    headers = {"Authorization": f"Bearer {test_setup['token_a']}"}

    # Create original contact
    await client.post(
        f"/api/v1/organisations/{org_id}/contacts",
        json={
            "contact_type": "CUSTOMER",
            "business_name": "Original Company Ltd",
            "vat_number": "GB 987 654 321",
        },
        headers=headers,
    )

    # Check duplicate with different spacing and lowercase VAT
    dup_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/check-duplicates",
        json={
            "business_name": "Different Name Inc",
            "vat_number": "gb987654321",
        },
        headers=headers,
    )
    assert dup_res.status_code == 200
    data = dup_res.json()
    assert data["has_duplicates"] is True
    assert len(data["matches"]) >= 1
    match = data["matches"][0]
    assert match["confidence"] == "HIGH"
    assert "vat_number" in match["matched_fields"]


async def test_duplicate_company_number_detection(client: AsyncClient, test_setup: dict):
    org_id = str(test_setup["org_a"].id)
    headers = {"Authorization": f"Bearer {test_setup['token_a']}"}

    await client.post(
        f"/api/v1/organisations/{org_id}/contacts",
        json={
            "contact_type": "SUPPLIER",
            "business_name": "Registered Entity Ltd",
            "company_number": "08765432",
        },
        headers=headers,
    )

    dup_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/check-duplicates",
        json={
            "business_name": "Another Name",
            "company_number": "08765432",
        },
        headers=headers,
    )
    assert dup_res.status_code == 200
    data = dup_res.json()
    assert data["has_duplicates"] is True
    assert "company_number" in data["matches"][0]["matched_fields"]


async def test_duplicate_business_name_normalization(client: AsyncClient, test_setup: dict):
    org_id = str(test_setup["org_a"].id)
    headers = {"Authorization": f"Bearer {test_setup['token_a']}"}

    # "Beta Solutions Limited"
    await client.post(
        f"/api/v1/organisations/{org_id}/contacts/quick",
        json={"business_name": "Beta Solutions Limited"},
        headers=headers,
    )

    # Check duplicate with "beta solutions ltd"
    dup_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/check-duplicates",
        json={"business_name": "beta solutions ltd"},
        headers=headers,
    )
    assert dup_res.status_code == 200
    data = dup_res.json()
    assert data["has_duplicates"] is True
    assert "business_name" in data["matches"][0]["matched_fields"]
