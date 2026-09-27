"""
Warp Ladger — Phase 1: Centralized Audit Logging Tests
Verifies that all mutations in Phase 1 create immutable, structured audit records.
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database.models import AuditLog

pytestmark = pytest.mark.asyncio


async def test_audit_logs_recorded_for_mutations(client: AsyncClient, test_setup: dict, db_session):
    org_a_id = str(test_setup["org_a"].id)
    token_a = test_setup["token_a"]

    # 1. Update organisation -> logs org.updated
    update_res = await client.patch(
        f"/api/v1/organisations/{org_a_id}",
        json={"timezone": "Europe/London"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert update_res.status_code == 200

    # 2. Suspend member -> logs member.suspended
    member_user_id = str(test_setup["user_a_member"].id)
    suspend_res = await client.patch(
        f"/api/v1/organisations/{org_a_id}/members/{member_user_id}/suspend",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert suspend_res.status_code == 200

    # 3. Retrieve audit logs via API
    audit_res = await client.get(
        f"/api/v1/organisations/{org_a_id}/audit/?limit=50",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert audit_res.status_code == 200
    res_json = audit_res.json()
    logs = res_json.get("data", res_json)
    actions = [entry["action"] for entry in logs]

    assert "org.updated" in actions
    assert "member.suspended" in actions


async def test_audit_log_tenant_isolation(client: AsyncClient, test_setup: dict):
    org_a_id = str(test_setup["org_a"].id)
    token_b = test_setup["token_b"]

    # User in Org B attempts to read Org A's audit log -> 403
    res = await client.get(
        f"/api/v1/organisations/{org_a_id}/audit/",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code in [403, 404]
