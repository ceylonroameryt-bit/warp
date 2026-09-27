"""
Warp Ladger — Phase 1: Organisation & Multi-Tenancy Tests
Verifies organisation creation, auto-assignment of Owner role,
organisation profile updates, multi-org membership, and cross-tenant boundaries.
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database.models import Organisation, Membership, Role

pytestmark = pytest.mark.asyncio


async def test_create_organisation_assigns_owner_role(client: AsyncClient, test_setup: dict, db_session):
    token_a = test_setup["token_a"]
    user_a = test_setup["user_a"]

    payload = {
        "name": "Highland Distilleries Ltd",
        "slug": f"highland-distilleries-{uuid.uuid4().hex[:6]}",
        "currency": "GBP",
        "timezone": "Europe/London",
    }

    res = await client.post(
        "/api/v1/organisations/",
        json=payload,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == payload["name"]
    assert data["currency"] == "GBP"
    new_org_id = uuid.UUID(data["id"])

    # Verify user_a has active membership with 'owner' role
    mem_res = await db_session.execute(
        select(Membership)
        .where(Membership.organisation_id == new_org_id)
        .where(Membership.user_id == user_a.id)
    )
    mem = mem_res.scalar_one()
    role_res = await db_session.execute(select(Role).where(Role.id == mem.role_id))
    role = role_res.scalar_one()
    assert role.name == "owner"


async def test_list_user_multiple_organisations(client: AsyncClient, test_setup: dict):
    token_a = test_setup["token_a"]

    res = await client.get(
        "/api/v1/organisations/",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res.status_code == 200
    orgs = res.json()
    assert len(orgs) >= 1
    assert any(o["name"] == "Acme Corp UK" for o in orgs)


async def test_cross_tenant_organisation_isolation(client: AsyncClient, test_setup: dict):
    org_a_id = str(test_setup["org_a"].id)
    token_b = test_setup["token_b"]  # Owner of Org B only

    # Org B user attempts to update Org A's profile
    patch_res = await client.patch(
        f"/api/v1/organisations/{org_a_id}",
        json={"name": "Hostile Takeover Corp"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    # User B is not a member of Org A -> 403 Forbidden
    assert patch_res.status_code in [403, 404]

    # Org B user attempts to delete Org A
    del_res = await client.delete(
        f"/api/v1/organisations/{org_a_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert del_res.status_code in [403, 404]
