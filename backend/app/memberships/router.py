"""Warp Ladger — Memberships Router"""
import uuid
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from app.core.dependencies import CurrentUser, DBSession, OrgMembership, require_permission
from app.memberships.service import MembershipService
from app.audit.service import AuditService

router = APIRouter()


class UpdateRoleRequest(BaseModel):
    role_id: uuid.UUID


@router.get("/", dependencies=[Depends(require_permission("member", "read"))])
async def list_members(org_id: uuid.UUID, db: DBSession, membership: OrgMembership):
    svc = MembershipService(db)
    members = await svc.list_members(org_id)
    return [
        {
            "user_id": str(m.user_id),
            "email": m.user.email,
            "full_name": m.user.full_name,
            "role": m.role.name,
            "role_id": str(m.role_id),
            "status": m.status.value,
            "joined_at": m.joined_at.isoformat() if m.joined_at else None,
        }
        for m in members
    ]


@router.patch(
    "/{user_id}/role",
    dependencies=[Depends(require_permission("member", "update"))],
)
async def update_member_role(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    body: UpdateRoleRequest,
    current_user: CurrentUser,
    db: DBSession,
    membership: OrgMembership,
):
    svc = MembershipService(db)
    m = await svc.update_member_role(
        org_id=org_id,
        target_user_id=user_id,
        new_role_id=body.role_id,
        actor_id=current_user.id,
    )
    audit = AuditService(db)
    await audit.log(
        action="member.role_changed",
        resource_type="membership",
        resource_id=str(user_id),
        organisation_id=org_id,
        user_id=current_user.id,
        diff={"new_role_id": str(body.role_id)},
    )
    return {"message": "Role updated."}


@router.patch(
    "/{user_id}/suspend",
    dependencies=[Depends(require_permission("member", "update"))],
)
async def suspend_member(
    org_id: uuid.UUID, user_id: uuid.UUID, current_user: CurrentUser,
    db: DBSession, membership: OrgMembership,
):
    svc = MembershipService(db)
    await svc.suspend_member(org_id=org_id, target_user_id=user_id, actor_id=current_user.id)
    audit = AuditService(db)
    await audit.log(
        action="member.suspended",
        resource_type="membership",
        resource_id=str(user_id),
        organisation_id=org_id,
        user_id=current_user.id,
    )
    return {"message": "Member suspended."}


@router.patch(
    "/{user_id}/reactivate",
    dependencies=[Depends(require_permission("member", "update"))],
)
async def reactivate_member(
    org_id: uuid.UUID, user_id: uuid.UUID, current_user: CurrentUser,
    db: DBSession, membership: OrgMembership,
):
    svc = MembershipService(db)
    await svc.reactivate_member(org_id=org_id, target_user_id=user_id)
    audit = AuditService(db)
    await audit.log(
        action="member.reactivated",
        resource_type="membership",
        resource_id=str(user_id),
        organisation_id=org_id,
        user_id=current_user.id,
    )
    return {"message": "Member reactivated."}


@router.delete(
    "/{user_id}",
    status_code=204,
    dependencies=[Depends(require_permission("member", "remove"))],
)
async def remove_member(
    org_id: uuid.UUID, user_id: uuid.UUID, current_user: CurrentUser,
    db: DBSession, membership: OrgMembership,
):
    svc = MembershipService(db)
    await svc.remove_member(
        org_id=org_id, target_user_id=user_id, actor_id=current_user.id
    )
    audit = AuditService(db)
    await audit.log(
        action="member.removed",
        resource_type="membership",
        resource_id=str(user_id),
        organisation_id=org_id,
        user_id=current_user.id,
    )
