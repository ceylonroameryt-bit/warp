"""
Warp Ladger — Organisations Router
"""
import uuid

from fastapi import APIRouter, Depends

from app.audit.service import AuditService
from app.core.dependencies import CurrentUser, DBSession, VerifiedUser, require_permission
from app.organisations.schemas import (
    CreateOrganisationRequest,
    OrganisationDetailResponse,
    OrganisationResponse,
    UpdateOrganisationRequest,
)
from app.organisations.service import OrganisationService

router = APIRouter()


@router.get("/", response_model=list[OrganisationResponse])
async def list_my_organisations(current_user: VerifiedUser, db: DBSession):
    """List all organisations the current user belongs to."""
    svc = OrganisationService(db)
    return await svc.list_user_organisations(current_user.id)


@router.post("/", response_model=OrganisationDetailResponse, status_code=201)
async def create_organisation(
    body: CreateOrganisationRequest,
    current_user: VerifiedUser,
    db: DBSession,
):
    """Create a new organisation. Current user becomes the owner."""
    svc = OrganisationService(db)
    org = await svc.create_organisation(
        name=body.name,
        owner_id=current_user.id,
        slug=body.slug,
        currency=body.currency,
        timezone=body.timezone,
    )
    audit = AuditService(db)
    await audit.log(
        action="org.created",
        resource_type="organisation",
        resource_id=str(org.id),
        organisation_id=org.id,
        user_id=current_user.id,
    )
    return org


@router.get("/{org_id}", response_model=OrganisationDetailResponse)
async def get_organisation(
    org_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    svc = OrganisationService(db)
    return await svc.get_organisation(org_id)


@router.patch(
    "/{org_id}",
    response_model=OrganisationDetailResponse,
    dependencies=[Depends(require_permission("org", "update"))],
)
async def update_organisation(
    org_id: uuid.UUID,
    body: UpdateOrganisationRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    svc = OrganisationService(db)
    org = await svc.update_organisation(
        org_id, updates=body.model_dump(exclude_none=True)
    )
    audit = AuditService(db)
    await audit.log(
        action="org.updated",
        resource_type="organisation",
        resource_id=str(org_id),
        organisation_id=org_id,
        user_id=current_user.id,
    )
    return org


@router.delete(
    "/{org_id}",
    status_code=204,
    dependencies=[Depends(require_permission("org", "delete"))],
)
async def delete_organisation(
    org_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    svc = OrganisationService(db)
    await svc.soft_delete_organisation(org_id)
    audit = AuditService(db)
    await audit.log(
        action="org.deleted",
        resource_type="organisation",
        resource_id=str(org_id),
        organisation_id=org_id,
        user_id=current_user.id,
    )
