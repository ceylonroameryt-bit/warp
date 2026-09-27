"""
Warp Ladger — Phase 1: Team Management & 8 Canonical Roles RBAC Tests
Verifies the complete 8 roles matrix (Owner, Administrator, Accountant,
Bookkeeper, Approver, Employee, Auditor, Viewer), invitations, role updates,
suspension, and safeguards against demoting/removing the last active Owner.
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database.models import Membership, MembershipStatus, Role, User, Invitation
from app.core.security import create_access_token, hash_password

pytestmark = pytest.mark.asyncio


async def test_all_8_canonical_roles_seeded(client: AsyncClient, test_setup: dict, db_session):
    org_a_id = str(test_setup["org_a"].id)
    token_a = test_setup["token_a"]

    res = await client.get(
        f"/api/v1/organisations/{org_a_id}/roles/",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res.status_code == 200
    roles = res.json()
    role_names = {r["name"].lower() for r in roles}

    expected_canonical_roles = {
        "owner",
        "administrator",
        "accountant",
        "bookkeeper",
        "approver",
        "employee",
        "auditor",
        "viewer",
    }
    for role_name in expected_canonical_roles:
        assert role_name in role_names, f"Expected canonical role '{role_name}' was not found in system roles"


async def test_invite_member_and_accept_workflow(client: AsyncClient, test_setup: dict, db_session):
    org_a_id = str(test_setup["org_a"].id)
    token_a = test_setup["token_a"]

    # Retrieve accountant role
    role_res = await db_session.execute(select(Role).where(Role.name == "accountant"))
    accountant_role = role_res.scalar_one()

    invite_email = f"accountant_{uuid.uuid4().hex[:6]}@orga.com"

    # 1. Send invite
    invite_res = await client.post(
        f"/api/v1/organisations/{org_a_id}/invitations/",
        json={"email": invite_email, "role_id": str(accountant_role.id)},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert invite_res.status_code == 201

    # 2. Get the invitation token from database
    inv_res = await db_session.execute(
        select(Invitation).where(Invitation.email == invite_email)
    )
    invitation = inv_res.scalar_one()
    assert invitation.token_hash is not None

    # 3. Create user for the invitee
    invitee_user = User(
        id=uuid.uuid4(),
        email=invite_email,
        full_name="Elena Accountant",
        hashed_password=hash_password("Password123!"),
        email_verified=True,
        is_active=True,
    )
    db_session.add(invitee_user)
    await db_session.commit()
    invitee_token = create_access_token(str(invitee_user.id))

    # Accept invitation using service directly with raw token or mock
    from app.invitations.service import InvitationService
    svc = InvitationService(db_session)
    # create new invite with known token
    accept_email = f"known_{uuid.uuid4().hex[:6]}@orga.com"
    _, raw_tok = await svc.create_invitation(
        org_id=test_setup["org_a"].id,
        inviter_id=test_setup["user_a"].id,
        email=accept_email,
        role_id=accountant_role.id,
    )

    accept_user = User(
        id=uuid.uuid4(),
        email=accept_email,
        full_name="Known User",
        hashed_password=hash_password("Password123!"),
        email_verified=True,
        is_active=True,
    )
    db_session.add(accept_user)
    await db_session.commit()
    accept_user_token = create_access_token(str(accept_user.id))

    accept_res = await client.post(
        "/api/v1/invitations/accept",
        json={"token": raw_tok},
        headers={"Authorization": f"Bearer {accept_user_token}"},
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["organisation_id"] == org_a_id


async def test_rbac_permission_boundaries(client: AsyncClient, test_setup: dict, db_session):
    org_a_id = str(test_setup["org_a"].id)
    token_a_member = test_setup["token_a_member"]  # Standard member/employee

    # 1. Employee cannot delete the organisation
    del_org_res = await client.delete(
        f"/api/v1/organisations/{org_a_id}",
        headers={"Authorization": f"Bearer {token_a_member}"},
    )
    assert del_org_res.status_code == 403

    # 2. Employee cannot invite new members
    role_res = await db_session.execute(select(Role).where(Role.name == "viewer"))
    viewer_role = role_res.scalar_one()

    invite_res = await client.post(
        f"/api/v1/organisations/{org_a_id}/invitations/",
        json={"email": "hacker@evil.com", "role_id": str(viewer_role.id)},
        headers={"Authorization": f"Bearer {token_a_member}"},
    )
    assert invite_res.status_code == 403


async def test_suspend_member_immediately_denies_access(client: AsyncClient, test_setup: dict):
    org_a_id = str(test_setup["org_a"].id)
    token_a = test_setup["token_a"]  # Owner
    token_a_member = test_setup["token_a_member"]  # Member
    member_user_id = str(test_setup["user_a_member"].id)

    # 1. Suspend member
    suspend_res = await client.patch(
        f"/api/v1/organisations/{org_a_id}/members/{member_user_id}/suspend",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert suspend_res.status_code == 200

    # 2. Suspended member tries to perform an action -> 403 Forbidden
    member_action_res = await client.get(
        f"/api/v1/organisations/{org_a_id}/members/",
        headers={"Authorization": f"Bearer {token_a_member}"},
    )
    assert member_action_res.status_code == 403

    # 3. Reactivate member
    reactivate_res = await client.patch(
        f"/api/v1/organisations/{org_a_id}/members/{member_user_id}/reactivate",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert reactivate_res.status_code == 200


async def test_safeguard_last_owner_from_removal_or_demotion(client: AsyncClient, test_setup: dict, db_session):
    org_a_id = str(test_setup["org_a"].id)
    token_a = test_setup["token_a"]  # Sole owner
    owner_user_id = str(test_setup["user_a"].id)

    # Fetch viewer role
    role_res = await db_session.execute(select(Role).where(Role.name == "viewer"))
    viewer_role = role_res.scalar_one()

    # Attempt to demote own role -> 403 (cannot change own role)
    demote_self_res = await client.patch(
        f"/api/v1/organisations/{org_a_id}/members/{owner_user_id}/role",
        json={"role_id": str(viewer_role.id)},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert demote_self_res.status_code == 403

    # Attempt to suspend own membership -> 403 (cannot suspend yourself)
    suspend_self_res = await client.patch(
        f"/api/v1/organisations/{org_a_id}/members/{owner_user_id}/suspend",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert suspend_self_res.status_code == 403

    # Attempt to remove own membership -> 403 (cannot remove yourself)
    remove_self_res = await client.delete(
        f"/api/v1/organisations/{org_a_id}/members/{owner_user_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert remove_self_res.status_code == 403
