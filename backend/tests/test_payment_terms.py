"""
Warp Ladger — Payment Terms API Tests
Section 11 & Section 37 Compliance.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_payment_terms_auto_seed_and_list(client: AsyncClient, test_setup: dict):
    org_id = str(test_setup["org_a"].id)
    headers = {"Authorization": f"Bearer {test_setup['token_a']}"}

    res = await client.get(f"/api/v1/organisations/{org_id}/payment-terms", headers=headers)
    assert res.status_code == 200
    terms = res.json()
    assert len(terms) >= 6
    names = [t["name"] for t in terms]
    assert "Due immediately" in names
    assert "30 days" in names
    assert "End of next month" in names


async def test_create_and_update_custom_payment_term(client: AsyncClient, test_setup: dict):
    org_id = str(test_setup["org_a"].id)
    headers = {"Authorization": f"Bearer {test_setup['token_a']}"}

    create_res = await client.post(
        f"/api/v1/organisations/{org_id}/payment-terms",
        json={
            "name": "Custom 21 Days",
            "term_type": "DAYS_AFTER_INVOICE",
            "days": 21,
            "is_default_customer": True,
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    data = create_res.json()
    term_id = data["id"]
    assert data["name"] == "Custom 21 Days"
    assert data["is_default_customer"] is True

    # Update term
    update_res = await client.patch(
        f"/api/v1/organisations/{org_id}/payment-terms/{term_id}",
        json={"days": 25, "name": "Custom 25 Days"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["days"] == 25
    assert update_res.json()["name"] == "Custom 25 Days"


async def test_assign_payment_term_to_contact(client: AsyncClient, test_setup: dict):
    org_id = str(test_setup["org_a"].id)
    headers = {"Authorization": f"Bearer {test_setup['token_a']}"}

    # Get terms
    terms = (await client.get(f"/api/v1/organisations/{org_id}/payment-terms", headers=headers)).json()
    term_30 = next(t for t in terms if t["days"] == 30)

    # Create contact with term
    c_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts",
        json={
            "contact_type": "CUSTOMER",
            "business_name": "Terms Client Ltd",
            "payment_terms_id": term_30["id"],
        },
        headers=headers,
    )
    assert c_res.status_code == 201
    data = c_res.json()
    assert data["payment_terms_name"] == term_30["name"]
