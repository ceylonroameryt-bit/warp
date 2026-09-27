"""Warp Ladger — Roles Router"""
import uuid
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from app.core.dependencies import DBSession, OrgMembership, require_permission
from app.roles.service import RoleService

router = APIRouter()


class CreateRoleRequest(BaseModel):
    name: str
    description: Optional[str] = None
    permission_ids: list[uuid.UUID] = []


@router.get("/", dependencies=[Depends(require_permission("role", "read"))])
async def list_roles(org_id: uuid.UUID, db: DBSession, membership: OrgMembership):
    svc = RoleService(db)
    roles = await svc.list_roles(org_id)
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "description": r.description,
            "is_system": r.is_system,
            "permissions": [
                {"name": rp.permission.name, "resource": rp.permission.resource, "action": rp.permission.action}
                for rp in r.role_permissions
            ],
        }
        for r in roles
    ]


@router.post(
    "/",
    status_code=201,
    dependencies=[Depends(require_permission("role", "create"))],
)
async def create_role(
    org_id: uuid.UUID, body: CreateRoleRequest, db: DBSession, membership: OrgMembership
):
    svc = RoleService(db)
    role = await svc.create_role(
        org_id=org_id,
        name=body.name,
        description=body.description,
        permission_ids=body.permission_ids,
    )
    return {"id": str(role.id), "name": role.name, "description": role.description}
