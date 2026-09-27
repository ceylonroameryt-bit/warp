"""Warp Ladger — Audit Log Router"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.audit.service import AuditService
from app.core.dependencies import DBSession, OrgMembership, require_permission

router = APIRouter()


@router.get(
    "/",
    dependencies=[Depends(require_permission("audit", "read"))],
)
async def list_audit_log(
    org_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    resource_type: Optional[str] = Query(default=None),
):
    svc = AuditService(db)
    events, total = await svc.list_events(
        organisation_id=org_id,
        page=page,
        page_size=page_size,
        resource_type=resource_type,
    )
    return {
        "data": [
            {
                "id": str(e.id),
                "action": e.action,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "user_id": str(e.user_id) if e.user_id else None,
                "created_at": e.created_at.isoformat(),
                "diff": e.diff,
                "ip_address": e.ip_address,
            }
            for e in events
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
