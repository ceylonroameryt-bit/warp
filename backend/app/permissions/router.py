"""Warp Ladger — Permissions Router (system permissions catalogue)"""
from fastapi import APIRouter
from app.core.dependencies import CurrentUser, DBSession
from sqlalchemy import select
from app.database.models import Permission

router = APIRouter()


@router.get("/")
async def list_permissions(current_user: CurrentUser, db: DBSession):
    """Return all system permissions (for role builder UI)."""
    result = await db.execute(select(Permission).where(Permission.is_system.is_(True)).order_by(Permission.resource, Permission.action))
    perms = result.scalars().all()
    return [
        {"id": str(p.id), "name": p.name, "resource": p.resource, "action": p.action, "description": p.description}
        for p in perms
    ]
