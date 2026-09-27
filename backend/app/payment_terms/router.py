"""
Warp Ladger — Payment Terms Router
Endpoints under /api/v1/organisations/{org_id}/payment-terms
"""
import uuid

from fastapi import APIRouter, Depends, Query, Request

from app.audit.service import AuditService
from app.core.dependencies import CurrentUser, DBSession, OrgMembership, require_permission
from app.payment_terms.schemas import PaymentTermCreate, PaymentTermResponse, PaymentTermUpdate
from app.payment_terms.service import PaymentTermsService

router = APIRouter()


@router.get(
    "",
    response_model=list[PaymentTermResponse],
    dependencies=[Depends(require_permission("payment_terms", "read"))],
)
async def list_payment_terms(
    org_id: uuid.UUID,
    membership: OrgMembership,
    db: DBSession,
    active_only: bool = Query(default=False),
):
    return await PaymentTermsService.list_terms(db, org_id, active_only=active_only)


@router.post(
    "",
    response_model=PaymentTermResponse,
    status_code=201,
    dependencies=[Depends(require_permission("payment_terms", "manage"))],
)
async def create_payment_term(
    org_id: uuid.UUID,
    data: PaymentTermCreate,
    membership: OrgMembership,
    current_user: CurrentUser,
    db: DBSession,
    request: Request,
):
    term = await PaymentTermsService.create_term(db, org_id, data)
    await AuditService.log(
        db=db,
        action="PAYMENT_TERM_CREATED",
        resource_type="payment_terms",
        resource_id=str(term.id),
        organisation_id=org_id,
        user_id=current_user.id,
        diff={"name": term.name, "days": term.days, "term_type": term.term_type.value},
        request=request,
    )
    return term


@router.get(
    "/{term_id}",
    response_model=PaymentTermResponse,
    dependencies=[Depends(require_permission("payment_terms", "read"))],
)
async def get_payment_term(
    org_id: uuid.UUID,
    term_id: uuid.UUID,
    membership: OrgMembership,
    db: DBSession,
):
    return await PaymentTermsService.get_term(db, org_id, term_id)


@router.patch(
    "/{term_id}",
    response_model=PaymentTermResponse,
    dependencies=[Depends(require_permission("payment_terms", "manage"))],
)
async def update_payment_term(
    org_id: uuid.UUID,
    term_id: uuid.UUID,
    data: PaymentTermUpdate,
    membership: OrgMembership,
    current_user: CurrentUser,
    db: DBSession,
    request: Request,
):
    term, diff = await PaymentTermsService.update_term(db, org_id, term_id, data)
    if diff:
        await AuditService.log(
            db=db,
            action="PAYMENT_TERMS_CHANGED",
            resource_type="payment_terms",
            resource_id=str(term.id),
            organisation_id=org_id,
            user_id=current_user.id,
            diff=diff,
            request=request,
        )
    return term


@router.delete(
    "/{term_id}",
    status_code=204,
    dependencies=[Depends(require_permission("payment_terms", "manage"))],
)
async def delete_payment_term(
    org_id: uuid.UUID,
    term_id: uuid.UUID,
    membership: OrgMembership,
    current_user: CurrentUser,
    db: DBSession,
    request: Request,
):
    await PaymentTermsService.delete_term(db, org_id, term_id)
    await AuditService.log(
        db=db,
        action="PAYMENT_TERM_DEACTIVATED",
        resource_type="payment_terms",
        resource_id=str(term_id),
        organisation_id=org_id,
        user_id=current_user.id,
        request=request,
    )
