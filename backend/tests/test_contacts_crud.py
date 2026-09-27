"""
Warp Ladger — Contact CRUD, Sub-resources, and Lifecycle Tests
"""
import uuid
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_create_customer_with_primary_person_and_address(client: AsyncClient, test_setup: dict):
    org_id = str(test_setup["org_a"].id)
    headers = {"Authorization": f"Bearer {test_setup['token_a']}"}

    payload = {
        "contact_type": "CUSTOMER",
        "business_name": "Apex Innovations Ltd",
        "legal_name": "Apex Innovations Limited",
        "email": "contact@apexinnovations.co.uk",
        "phone": "+44 20 7946 0912",
        "company_number": "12345678",
        "vat_number": "GB123456789",
        "currency": "GBP",
        "primary_contact": {
            "first_name": "Jane",
            "last_name": "Doe",
            "job_title": "Finance Director",
            "email": "jane@apexinnovations.co.uk",
            "phone": "+44 20 7946 0913",
            "is_primary": True,
        },
        "billing_address": {
            "address_type": "BILLING",
            "line1": "100 King Street",
            "city": "London",
            "postcode": "EC2V 7AY",
            "country_code": "GB",
            "is_primary": True,
        },
    }

    response = await client.post(f"/api/v1/organisations/{org_id}/contacts", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["business_name"] == "Apex Innovations Ltd"
    assert data["contact_type"] == "CUSTOMER"
    assert data["primary_contact_name"] == "Jane Doe"
    assert data["primary_contact_email"] == "jane@apexinnovations.co.uk"
    contact_id = data["id"]

    # Verify detail view
    detail_res = await client.get(f"/api/v1/organisations/{org_id}/contacts/{contact_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert len(detail["people"]) == 1
    assert detail["people"][0]["first_name"] == "Jane"
    assert detail["people"][0]["is_primary"] is True
    assert len(detail["addresses"]) == 1
    assert detail["addresses"][0]["city"] == "London"


async def test_quick_create_contact(client: AsyncClient, test_setup: dict):
    org_id = str(test_setup["org_a"].id)
    headers = {"Authorization": f"Bearer {test_setup['token_a']}"}

    payload = {
        "contact_type": "SUPPLIER",
        "business_name": "Quick Parts Supply",
        "email": "orders@quickparts.co.uk",
    }
    res = await client.post(f"/api/v1/organisations/{org_id}/contacts/quick", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["business_name"] == "Quick Parts Supply"
    assert data["contact_type"] == "SUPPLIER"
    assert data["status"] == "ACTIVE"


async def test_contact_type_both(client: AsyncClient, test_setup: dict):
    org_id = str(test_setup["org_a"].id)
    headers = {"Authorization": f"Bearer {test_setup['token_a']}"}

    payload = {
        "contact_type": "BOTH",
        "business_name": "Global Trade Logistics",
        "email": "info@globaltrade.com",
    }
    res = await client.post(f"/api/v1/organisations/{org_id}/contacts", json=payload, headers=headers)
    assert res.status_code == 201
    assert res.json()["contact_type"] == "BOTH"


async def test_update_contact_and_activity_feed(client: AsyncClient, test_setup: dict):
    org_id = str(test_setup["org_a"].id)
    headers = {"Authorization": f"Bearer {test_setup['token_a']}"}

    # Create
    create_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/quick",
        json={"business_name": "Modifiable Ltd", "email": "test@mod.com"},
        headers=headers,
    )
    contact_id = create_res.json()["id"]

    # Update
    update_res = await client.patch(
        f"/api/v1/organisations/{org_id}/contacts/{contact_id}",
        json={"business_name": "Modifiable Solutions Ltd", "phone": "+44 123 456"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["business_name"] == "Modifiable Solutions Ltd"

    # Check Activity
    act_res = await client.get(f"/api/v1/organisations/{org_id}/contacts/{contact_id}/activity", headers=headers)
    assert act_res.status_code == 200
    activity = act_res.json()
    actions = [a["action"] for a in activity]
    assert "CONTACT_UPDATED" in actions


async def test_archive_and_restore_contact(client: AsyncClient, test_setup: dict):
    org_id = str(test_setup["org_a"].id)
    headers = {"Authorization": f"Bearer {test_setup['token_a']}"}

    c_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/quick",
        json={"business_name": "Archive Me Inc"},
        headers=headers,
    )
    contact_id = c_res.json()["id"]

    # Archive
    arc_res = await client.post(f"/api/v1/organisations/{org_id}/contacts/{contact_id}/archive", headers=headers)
    assert arc_res.status_code == 200
    assert arc_res.json()["status"] == "ARCHIVED"

    # List default hides ARCHIVED
    list_res = await client.get(f"/api/v1/organisations/{org_id}/contacts", headers=headers)
    ids = [item["id"] for item in list_res.json()["items"]]
    assert contact_id not in ids

    # List with status=ARCHIVED shows it
    arc_list = await client.get(f"/api/v1/organisations/{org_id}/contacts?status=ARCHIVED", headers=headers)
    arc_ids = [item["id"] for item in arc_list.json()["items"]]
    assert contact_id in arc_ids

    # Restore
    res_res = await client.post(f"/api/v1/organisations/{org_id}/contacts/{contact_id}/restore", headers=headers)
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "ACTIVE"


async def test_contact_people_lifecycle(client: AsyncClient, test_setup: dict):
    org_id = str(test_setup["org_a"].id)
    headers = {"Authorization": f"Bearer {test_setup['token_a']}"}

    c_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/quick",
        json={"business_name": "Multi People Corp"},
        headers=headers,
    )
    contact_id = c_res.json()["id"]

    # Add person 1 (primary)
    p1_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/{contact_id}/people",
        json={"first_name": "Person", "last_name": "One", "is_primary": True},
        headers=headers,
    )
    assert p1_res.status_code == 201
    p1_id = p1_res.json()["id"]
    assert p1_res.json()["is_primary"] is True

    # Add person 2 (set as primary, should demote person 1)
    p2_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/{contact_id}/people",
        json={"first_name": "Person", "last_name": "Two", "is_primary": True},
        headers=headers,
    )
    assert p2_res.status_code == 201
    assert p2_res.json()["is_primary"] is True

    # Verify detail shows person 2 is primary, person 1 is not
    detail = (await client.get(f"/api/v1/organisations/{org_id}/contacts/{contact_id}", headers=headers)).json()
    people_map = {p["id"]: p["is_primary"] for p in detail["people"]}
    assert people_map[p1_id] is False

    # Delete person 1
    del_res = await client.delete(f"/api/v1/organisations/{org_id}/contacts/{contact_id}/people/{p1_id}", headers=headers)
    assert del_res.status_code == 204


async def test_contact_notes(client: AsyncClient, test_setup: dict):
    org_id = str(test_setup["org_a"].id)
    headers = {"Authorization": f"Bearer {test_setup['token_a']}"}

    c_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/quick",
        json={"business_name": "Noted Client"},
        headers=headers,
    )
    contact_id = c_res.json()["id"]

    # Add note
    note_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/{contact_id}/notes",
        json={"content": "Customer prefers consolidated monthly invoices."},
        headers=headers,
    )
    assert note_res.status_code == 201
    assert note_res.json()["content"] == "Customer prefers consolidated monthly invoices."

    # List notes
    notes_list = await client.get(f"/api/v1/organisations/{org_id}/contacts/{contact_id}/notes", headers=headers)
    assert len(notes_list.json()) == 1
