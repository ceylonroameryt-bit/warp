"""Warp Ladger — Invitations Router"""
import uuid
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.dependencies import CurrentUser, DBSession, OrgMembership, require_permission
from app.core.email import EmailService
from app.database.models import Invitation, Organisation, Role
from app.invitations.service import InvitationService
from app.audit.service import AuditService

router = APIRouter()


class InviteRequest(BaseModel):
    email: EmailStr
    role_id: uuid.UUID


class AcceptInvitationRequest(BaseModel):
    token: str


@router.get("/", dependencies=[Depends(require_permission("member", "read"))])
async def list_pending_invitations(
    org_id: uuid.UUID, db: DBSession, membership: OrgMembership
):
    svc = InvitationService(db)
    invites = await svc.list_pending(org_id)
    return [
        {
            "id": str(i.id),
            "email": i.email,
            "role_id": str(i.role_id),
            "expires_at": i.expires_at.isoformat(),
            "created_at": i.created_at.isoformat(),
        }
        for i in invites
    ]


@router.post("/", status_code=201, dependencies=[Depends(require_permission("member", "invite"))])
async def create_invitation(
    org_id: uuid.UUID,
    body: InviteRequest,
    current_user: CurrentUser,
    db: DBSession,
    membership: OrgMembership,
):
    svc = InvitationService(db)
    invitation, raw_token = await svc.create_invitation(
        org_id=org_id,
        inviter_id=current_user.id,
        email=body.email,
        role_id=body.role_id,
    )
    # Fetch org and role names for email
    org_result = await db.execute(select(Organisation).where(Organisation.id == org_id))
    org = org_result.scalar_one()
    role_result = await db.execute(select(Role).where(Role.id == body.role_id))
    role = role_result.scalar_one()

    email_svc = EmailService()
    await email_svc.send_invitation_email(
        to_email=body.email,
        inviter_name=current_user.full_name,
        org_name=org.name,
        role_name=role.name,
        token=raw_token,
    )
    audit = AuditService(db)
    await audit.log(
        action="member.invited",
        resource_type="invitation",
        resource_id=str(invitation.id),
        organisation_id=org_id,
        user_id=current_user.id,
        diff={"email": body.email, "role_id": str(body.role_id)},
    )
    return {"message": f"Invitation sent to {body.email}."}


@router.delete(
    "/{invitation_id}",
    status_code=204,
    dependencies=[Depends(require_permission("member", "invite"))],
)
async def cancel_invitation(
    org_id: uuid.UUID,
    invitation_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
    membership: OrgMembership,
):
    svc = InvitationService(db)
    await svc.cancel_invitation(invitation_id=invitation_id, org_id=org_id)
    audit = AuditService(db)
    await audit.log(
        action="invitation.cancelled",
        resource_type="invitation",
        resource_id=str(invitation_id),
        organisation_id=org_id,
        user_id=current_user.id,
    )


# Public endpoint — no org membership required
public_router = APIRouter()

@public_router.post("/accept", status_code=200)
@router.post("/accept", status_code=200)
async def accept_invitation(
    body: AcceptInvitationRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Accept an invitation. User must be logged in."""
    svc = InvitationService(db)
    invitation = await svc.accept_invitation(
        token=body.token,
        accepting_user_id=current_user.id,
        accepting_email=current_user.email,
    )
    audit = AuditService(db)
    await audit.log(
        action="member.joined",
        resource_type="membership",
        resource_id=str(current_user.id),
        organisation_id=invitation.organisation_id,
        user_id=current_user.id,
        diff={"email": current_user.email, "role_id": str(invitation.role_id)},
    )
    return {
        "message": "Invitation accepted.",
        "organisation_id": str(invitation.organisation_id),
    }
