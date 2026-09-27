"""
Warp Ladger — Multi-Tenant Isolation & Cross-Tenant Security Tests
Section 5 & Section 37 Compliance.
"""
import uuid
import pytest
from httpx import AsyncClient

from app.database.models import File, PaymentTerm, PaymentTermType

pytestmark = pytest.mark.asyncio


async def test_cross_tenant_contact_access_denied(client: AsyncClient, test_setup: dict):
    org_a_id = str(test_setup["org_a"].id)
    org_b_id = str(test_setup["org_b"].id)
    token_a = test_setup["token_a"]
    token_b = test_setup["token_b"]

    # 1. Org A creates a contact
    create_res = await client.post(
        f"/api/v1/organisations/{org_a_id}/contacts/quick",
        json={"business_name": "Org A Secret Contact", "email": "secret@orga.com"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert create_res.status_code == 201
    contact_id = create_res.json()["id"]

    # 2. Org B user tries to access Org A's contact via Org A URL -> Not a member of Org A
    get_res_org_a = await client.get(
        f"/api/v1/organisations/{org_a_id}/contacts/{contact_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert get_res_org_a.status_code in [403, 404]

    # 3. Org B user tries to access Org A's contact ID via Org B URL -> Contact not in Org B
    get_res_org_b = await client.get(
        f"/api/v1/organisations/{org_b_id}/contacts/{contact_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert get_res_org_b.status_code == 404

    # 4. Org B user tries to update Org A's contact
    patch_res = await client.patch(
        f"/api/v1/organisations/{org_b_id}/contacts/{contact_id}",
        json={"business_name": "Hacked Name"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert patch_res.status_code == 404

    # 5. Org B user tries to archive Org A's contact
    arc_res = await client.post(
        f"/api/v1/organisations/{org_b_id}/contacts/{contact_id}/archive",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert arc_res.status_code == 404


async def test_cross_tenant_payment_terms_tampering_rejected(
    client: AsyncClient, test_setup: dict, db_session
):
    org_a_id = str(test_setup["org_a"].id)
    org_b_id = str(test_setup["org_b"].id)
    token_a = test_setup["token_a"]

    # Create a payment term explicitly in Org B
    term_b = PaymentTerm(
        organisation_id=test_setup["org_b"].id,
        name="Org B Term",
        term_type=PaymentTermType.DAYS_AFTER_INVOICE,
        days=45,
    )
    db_session.add(term_b)
    await db_session.commit()

    # User in Org A attempts to create a contact pointing to Org B's payment term ID
    malicious_payload = {
        "contact_type": "CUSTOMER",
        "business_name": "Tenant Tamper Corp",
        "payment_terms_id": str(term_b.id),
    }

    res = await client.post(
        f"/api/v1/organisations/{org_a_id}/contacts",
        json=malicious_payload,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res.status_code == 400
    assert "payment term" in res.text.lower()


async def test_cross_tenant_file_attachment_rejected(
    client: AsyncClient, test_setup: dict, db_session
):
    org_a_id = str(test_setup["org_a"].id)
    token_a = test_setup["token_a"]

    # Create contact in Org A
    c_res = await client.post(
        f"/api/v1/organisations/{org_a_id}/contacts/quick",
        json={"business_name": "Document Testing Ltd"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    contact_id = c_res.json()["id"]

    # Create a file belonging to Org B
    file_b = File(
        organisation_id=test_setup["org_b"].id,
        bucket="test-bucket",
        key="org-b/file.pdf",
        filename="contract.pdf",
        content_type="application/pdf",
        size_bytes=1024,
    )
    db_session.add(file_b)
    await db_session.commit()

    # Org A tries to attach Org B's file
    attach_res = await client.post(
        f"/api/v1/organisations/{org_a_id}/contacts/{contact_id}/documents",
        json={"file_id": str(file_b.id)},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert attach_res.status_code == 400
    assert "file not found or does not belong" in attach_res.text.lower()
