"""
Warp Ladger — Phase 1: End-to-End Core Verification Flow

Verifies the complete sequential chain:
Register
   ↓
Create Business
   ↓
Invite Team
   ↓
Assign Role
   ↓
Upload File
   ↓
Audit Event
"""
import io
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database.models import User, Role

pytestmark = pytest.mark.asyncio


async def test_complete_phase1_flow(client: AsyncClient, db_session):
    from app.roles.service import seed_permissions_and_roles
    await seed_permissions_and_roles(db_session)

    # ── Step 1: Register User ─────────────────────────────────
    email = f"founder_{uuid.uuid4().hex[:8]}@commercialcorp.co.uk"
    password = "MasterPassword2026!"
    full_name = "Eleanor Vance"

    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert reg_res.status_code == 201
    user_id = reg_res.json()["user_id"]

    # Verify user email to enable login
    user_q = await db_session.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = user_q.scalar_one()
    user.email_verified = True
    await db_session.commit()

    # Login and acquire auth tokens
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    access_token = login_res.json()["access_token"]
    auth_header = {"Authorization": f"Bearer {access_token}"}

    # ── Step 2: Create Business (Organisation) ─────────────────
    biz_payload = {
        "name": "Commercial Corp Ltd",
        "slug": f"commercial-corp-{uuid.uuid4().hex[:6]}",
        "currency": "GBP",
        "timezone": "Europe/London",
    }
    biz_res = await client.post(
        "/api/v1/organisations/",
        json=biz_payload,
        headers=auth_header,
    )
    assert biz_res.status_code == 201
    org_id = biz_res.json()["id"]

    # ── Step 3: Invite Team Member ────────────────────────────
    # Find accountant role
    acc_role_res = await db_session.execute(select(Role).where(Role.name == "accountant"))
    acc_role = acc_role_res.scalar_one()

    invite_email = f"lead_accountant_{uuid.uuid4().hex[:6]}@financials.co.uk"
    invite_res = await client.post(
        f"/api/v1/organisations/{org_id}/invitations/",
        json={"email": invite_email, "role_id": str(acc_role.id)},
        headers=auth_header,
    )
    assert invite_res.status_code == 201

    # ── Step 4: Assign / Update Role ──────────────────────────
    # Create colleague and add to org to test role change
    colleague = User(
        id=uuid.uuid4(),
        email=f"colleague_{uuid.uuid4().hex[:6]}@commercialcorp.co.uk",
        full_name="Mark Smith",
        hashed_password=user.hashed_password,
        email_verified=True,
        is_active=True,
    )
    db_session.add(colleague)
    await db_session.commit()

    # Find employee role and auditor role
    emp_role_res = await db_session.execute(select(Role).where(Role.name == "employee"))
    emp_role = emp_role_res.scalar_one()

    auditor_role_res = await db_session.execute(select(Role).where(Role.name == "auditor"))
    auditor_role = auditor_role_res.scalar_one()

    from app.database.models import Membership, MembershipStatus
    mem = Membership(
        user_id=colleague.id,
        organisation_id=uuid.UUID(org_id),
        role_id=emp_role.id,
        status=MembershipStatus.active,
    )
    db_session.add(mem)
    await db_session.commit()

    # Promote colleague to Auditor
    role_change_res = await client.patch(
        f"/api/v1/organisations/{org_id}/members/{colleague.id}/role",
        json={"role_id": str(auditor_role.id)},
        headers=auth_header,
    )
    assert role_change_res.status_code == 200

    # ── Step 5: Upload File (Receipt / Certificate) ────────────
    sample_pdf = b"%PDF-1.4 sample commercial incorporation certificate"
    upload_res = await client.post(
        f"/api/v1/files/organisations/{org_id}/upload",
        files={"upload": ("incorporation_certificate.pdf", io.BytesIO(sample_pdf), "application/pdf")},
        headers=auth_header,
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["id"]
    assert file_id is not None

    # ── Step 6: Verify Immutable Audit Event ──────────────────
    audit_res = await client.get(
        f"/api/v1/organisations/{org_id}/audit/?limit=50",
        headers=auth_header,
    )
    assert audit_res.status_code == 200
    res_json = audit_res.json()
    audit_events = res_json.get("data", res_json)
    actions = [e["action"] for e in audit_events]

    assert "org.created" in actions
    assert "member.invited" in actions
    assert "member.role_changed" in actions
    assert "file.uploaded" in actions
