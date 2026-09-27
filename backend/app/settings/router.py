"""Warp Ladger — Settings Router"""
import uuid
from typing import Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy import select
from app.core.dependencies import DBSession, OrgMembership, require_permission
from app.database.models import OrganisationSetting

router = APIRouter()


class UpsertSettingRequest(BaseModel):
    key: str
    value: Any


@router.get(
    "/organisations/{org_id}",
    dependencies=[Depends(require_permission("settings", "read"))],
)
async def get_org_settings(
    org_id: uuid.UUID, db: DBSession, membership: OrgMembership
):
    result = await db.execute(
        select(OrganisationSetting).where(OrganisationSetting.organisation_id == org_id)
    )
    settings = result.scalars().all()
    return {s.key: s.value for s in settings}


@router.put(
    "/organisations/{org_id}",
    dependencies=[Depends(require_permission("settings", "update"))],
)
async def upsert_org_setting(
    org_id: uuid.UUID,
    body: UpsertSettingRequest,
    db: DBSession,
    membership: OrgMembership,
):
    result = await db.execute(
        select(OrganisationSetting)
        .where(OrganisationSetting.organisation_id == org_id)
        .where(OrganisationSetting.key == body.key)
    )
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = body.value
    else:
        setting = OrganisationSetting(
            organisation_id=org_id, key=body.key, value=body.value
        )
        db.add(setting)
    await db.flush()
    return {"message": "Setting updated.", "key": body.key}
