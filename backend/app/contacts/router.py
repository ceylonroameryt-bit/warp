"""
Warp Ladger — Contacts Router
Endpoints under /api/v1/organisations/{org_id}/contacts
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile
from sqlalchemy import desc, select

from app.audit.service import AuditService
from app.contacts.schemas import (
    ContactAddressCreate,
    ContactAddressResponse,
    ContactAddressUpdate,
    ContactCreate,
    ContactDetailResponse,
    ContactDocumentAttach,
    ContactDocumentResponse,
    ContactImportExecuteRequest,
    ContactImportExecuteResult,
    ContactImportPreviewResult,
    ContactListResponse,
    ContactNoteCreate,
    ContactNoteResponse,
    ContactPersonCreate,
    ContactPersonResponse,
    ContactPersonUpdate,
    ContactQuickCreate,
    ContactResponse,
    ContactUpdate,
    DuplicateCheckRequest,
    DuplicateCheckResponse,
)
from app.contacts.service import ContactService
from app.core.dependencies import CurrentUser, DBSession, OrgMembership, require_permission
from app.database.models import AuditLog

router = APIRouter()


def _format_contact_response(c) -> ContactResponse:
    primary_person = None
    if c.people:
        for p in c.people:
            if p.is_primary:
                primary_person = p
                break
        if not primary_person and len(c.people) > 0:
            primary_person = c.people[0]

    p_name = None
    p_email = None
    p_phone = None
    if primary_person:
        p_name = f"{primary_person.first_name} {primary_person.last_name or ''}".strip()
        p_email = primary_person.email
        p_phone = primary_person.phone or primary_person.mobile

    return ContactResponse(
        id=c.id,
        organisation_id=c.organisation_id,
        contact_type=c.contact_type,
        business_name=c.business_name,
        legal_name=c.legal_name,
        display_name=c.display_name,
        first_name=c.first_name,
        last_name=c.last_name,
        email=c.email,
        phone=c.phone,
        mobile=c.mobile,
        website=c.website,
        company_number=c.company_number,
        vat_number=c.vat_number,
        tax_identifier=c.tax_identifier,
        currency=c.currency,
        payment_terms_id=c.payment_terms_id,
        reference=c.reference,
        credit_limit=float(c.credit_limit) if c.credit_limit is not None else None,
        notes=c.notes,
        status=c.status,
        primary_contact_name=p_name,
        primary_contact_email=p_email,
        primary_contact_phone=p_phone,
        payment_terms_name=c.payment_terms.name if c.payment_terms else None,
        created_at=c.created_at,
        updated_at=c.updated_at,
        archived_at=c.archived_at,
    )


# ─── Contact List & Search ───────────────────────────────────
@router.get(
    "",
    response_model=ContactListResponse,
    dependencies=[Depends(require_permission("contact", "read"))],
)
async def list_contacts(
    org_id: uuid.UUID,
    membership: OrgMembership,
    db: DBSession,
    contact_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    country_code: Optional[str] = Query(default=None),
    currency: Optional[str] = Query(default=None),
    payment_terms_id: Optional[uuid.UUID] = Query(default=None),
    sort_by: str = Query(default="name_asc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
):
    items, total = await ContactService.list_contacts(
        db=db,
        org_id=org_id,
        contact_type=contact_type,
        status=status,
        search=search,
        country_code=country_code,
        currency=currency,
        payment_terms_id=payment_terms_id,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return ContactListResponse(
        items=[_format_contact_response(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ─── Duplicate Check ─────────────────────────────────────────
@router.post(
    "/check-duplicates",
    response_model=DuplicateCheckResponse,
    dependencies=[Depends(require_permission("contact", "read"))],
)
async def check_duplicate_contact(
    org_id: uuid.UUID,
    data: DuplicateCheckRequest,
    membership: OrgMembership,
    db: DBSession,
):
    return await ContactService.check_duplicates(
        db=db,
        org_id=org_id,
        business_name=data.business_name,
        email=data.email,
        vat_number=data.vat_number,
        company_number=data.company_number,
        exclude_contact_id=data.exclude_contact_id,
    )


# ─── Create Contact ──────────────────────────────────────────
@router.post(
    "",
    response_model=ContactResponse,
    status_code=201,
    dependencies=[Depends(require_permission("contact", "create"))],
)
async def create_contact(
    org_id: uuid.UUID,
    data: ContactCreate,
    membership: OrgMembership,
    current_user: CurrentUser,
    db: DBSession,
    request: Request,
):
    contact = await ContactService.create_contact(
        db=db, org_id=org_id, data=data, current_user_id=current_user.id
    )
    await AuditService.log(
        db=db,
        action="CONTACT_CREATED",
        resource_type="contact",
        resource_id=str(contact.id),
        organisation_id=org_id,
        user_id=current_user.id,
        diff={"business_name": contact.business_name, "contact_type": contact.contact_type.value},
        request=request,
    )
    contact_loaded = await ContactService.get_contact(db, org_id, contact.id, load_details=False)
    return _format_contact_response(contact_loaded)


@router.post(
    "/quick",
    response_model=ContactResponse,
    status_code=201,
    dependencies=[Depends(require_permission("contact", "create"))],
)
async def quick_create_contact(
    org_id: uuid.UUID,
    data: ContactQuickCreate,
    membership: OrgMembership,
    current_user: CurrentUser,
    db: DBSession,
    request: Request,
):
    contact = await ContactService.quick_create(
        db=db, org_id=org_id, data=data, current_user_id=current_user.id
    )
    await AuditService.log(
        db=db,
        action="CONTACT_CREATED",
        resource_type="contact",
        resource_id=str(contact.id),
        organisation_id=org_id,
        user_id=current_user.id,
        diff={"business_name": contact.business_name, "type": "quick_create"},
        request=request,
    )
    contact_loaded = await ContactService.get_contact(db, org_id, contact.id, load_details=False)
    return _format_contact_response(contact_loaded)


# ─── Import & Export ─────────────────────────────────────────
@router.post(
    "/import/preview",
    response_model=ContactImportPreviewResult,
    dependencies=[Depends(require_permission("contact", "create"))],
)
async def preview_csv_import(
    org_id: uuid.UUID,
    membership: OrgMembership,
    db: DBSession,
    file: UploadFile = File(...),
):
    content = await file.read()
    text = content.decode("utf-8-sig", errors="replace")
    return await ContactService.preview_csv(db, org_id, text)


@router.post(
    "/import/execute",
    response_model=ContactImportExecuteResult,
    dependencies=[Depends(require_permission("contact", "create"))],
)
async def execute_csv_import(
    org_id: uuid.UUID,
    data: ContactImportExecuteRequest,
    membership: OrgMembership,
    current_user: CurrentUser,
    db: DBSession,
    request: Request,
):
    created, skipped, errors = await ContactService.execute_csv_import(
        db=db, org_id=org_id, rows=data.rows, skip_errors=data.skip_errors, user_id=current_user.id
    )
    await AuditService.log(
        db=db,
        action="CONTACT_IMPORT_COMPLETED",
        resource_type="contact",
        organisation_id=org_id,
        user_id=current_user.id,
        diff={"created_count": created, "skipped_count": skipped},
        request=request,
    )
    return ContactImportExecuteResult(
        created_count=created,
        skipped_count=skipped,
        errors=errors,
    )


@router.get(
    "/export",
    dependencies=[Depends(require_permission("contact", "export"))],
)
async def export_contacts(
    org_id: uuid.UUID,
    membership: OrgMembership,
    current_user: CurrentUser,
    db: DBSession,
    request: Request,
    contact_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    csv_data = await ContactService.export_contacts_to_csv(
        db=db, org_id=org_id, contact_type=contact_type, status=status
    )
    await AuditService.log(
        db=db,
        action="CONTACT_EXPORT_CREATED",
        resource_type="contact",
        organisation_id=org_id,
        user_id=current_user.id,
        diff={"contact_type": contact_type, "status": status},
        request=request,
    )
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=contacts_{org_id}.csv"},
    )


# ─── Contact Detail ──────────────────────────────────────────
@router.get(
    "/{contact_id}",
    response_model=ContactDetailResponse,
    dependencies=[Depends(require_permission("contact", "read"))],
)
async def get_contact_detail(
    org_id: uuid.UUID,
    contact_id: uuid.UUID,
    membership: OrgMembership,
    db: DBSession,
):
    contact = await ContactService.get_contact(db, org_id, contact_id, load_details=True)
    documents = await ContactService.list_documents(db, org_id, contact_id)
    notes_resp = [
        ContactNoteResponse(
            id=n.id,
            contact_id=n.contact_id,
            organisation_id=n.organisation_id,
            content=n.content,
            created_by_id=n.created_by_id,
            created_by_name=n.created_by.full_name or n.created_by.email if n.created_by else None,
            created_at=n.created_at,
        )
        for n in contact.internal_notes
    ]

    base_resp = _format_contact_response(contact)
    return ContactDetailResponse(
        **base_resp.model_dump(),
        people=[ContactPersonResponse.model_validate(p) for p in contact.people],
        addresses=[ContactAddressResponse.model_validate(a) for a in contact.addresses],
        internal_notes=notes_resp,
        documents=documents,
        tags=[t.name for t in contact.tags],
    )


@router.patch(
    "/{contact_id}",
    response_model=ContactResponse,
    dependencies=[Depends(require_permission("contact", "update"))],
)
async def update_contact(
    org_id: uuid.UUID,
    contact_id: uuid.UUID,
    data: ContactUpdate,
    membership: OrgMembership,
    current_user: CurrentUser,
    db: DBSession,
    request: Request,
):
    contact, diff = await ContactService.update_contact(db, org_id, contact_id, data)
    if diff:
        await AuditService.log(
            db=db,
            action="CONTACT_UPDATED",
            resource_type="contact",
            resource_id=str(contact.id),
            organisation_id=org_id,
            user_id=current_user.id,
            diff=diff,
            request=request,
        )
    return _format_contact_response(contact)


@router.post(
    "/{contact_id}/archive",
    response_model=ContactResponse,
    dependencies=[Depends(require_permission("contact", "archive"))],
)
async def archive_contact(
    org_id: uuid.UUID,
    contact_id: uuid.UUID,
    membership: OrgMembership,
    current_user: CurrentUser,
    db: DBSession,
    request: Request,
):
    contact = await ContactService.archive_contact(db, org_id, contact_id)
    await AuditService.log(
        db=db,
        action="CONTACT_ARCHIVED",
        resource_type="contact",
        resource_id=str(contact.id),
        organisation_id=org_id,
        user_id=current_user.id,
        request=request,
    )
    return _format_contact_response(contact)


@router.post(
    "/{contact_id}/restore",
    response_model=ContactResponse,
    dependencies=[Depends(require_permission("contact", "archive"))],
)
async def restore_contact(
    org_id: uuid.UUID,
    contact_id: uuid.UUID,
    membership: OrgMembership,
    current_user: CurrentUser,
    db: DBSession,
    request: Request,
):
    contact = await ContactService.restore_contact(db, org_id, contact_id)
    await AuditService.log(
        db=db,
        action="CONTACT_RESTORED",
        resource_type="contact",
        resource_id=str(contact.id),
        organisation_id=org_id,
        user_id=current_user.id,
        request=request,
    )
    return _format_contact_response(contact)


@router.get(
    "/{contact_id}/activity",
    dependencies=[Depends(require_permission("contact", "read"))],
)
async def get_contact_activity(
    org_id: uuid.UUID,
    contact_id: uuid.UUID,
    membership: OrgMembership,
    db: DBSession,
):
    # Verify contact belongs to this org
    await ContactService.get_contact(db, org_id, contact_id)
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.organisation_id == org_id)
        .where(AuditLog.resource_id == str(contact_id))
        .order_by(AuditLog.created_at.desc())
        .limit(100)
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(l.id),
            "action": l.action,
            "diff": l.diff,
            "created_at": l.created_at.isoformat(),
            "user_id": str(l.user_id) if l.user_id else None,
        }
        for l in logs
    ]


# ─── Contact People ──────────────────────────────────────────
@router.post(
    "/{contact_id}/people",
    response_model=ContactPersonResponse,
    status_code=201,
    dependencies=[Depends(require_permission("contact", "update"))],
)
async def add_contact_person(
    org_id: uuid.UUID,
    contact_id: uuid.UUID,
    data: ContactPersonCreate,
    membership: OrgMembership,
    current_user: CurrentUser,
    db: DBSession,
    request: Request,
):
    person = await ContactService.add_person(db, org_id, contact_id, data)
    await AuditService.log(
        db=db,
        action="CONTACT_PERSON_ADDED",
        resource_type="contact",
        resource_id=str(contact_id),
        organisation_id=org_id,
        user_id=current_user.id,
        diff={"person_name": f"{person.first_name} {person.last_name or ''}".strip()},
        request=request,
    )
    return person


@router.patch(
    "/{contact_id}/people/{person_id}",
    response_model=ContactPersonResponse,
    dependencies=[Depends(require_permission("contact", "update"))],
)
async def update_contact_person(
    org_id: uuid.UUID,
    contact_id: uuid.UUID,
    person_id: uuid.UUID,
    data: ContactPersonUpdate,
    membership: OrgMembership,
    current_user: CurrentUser,
    db: DBSession,
    request: Request,
):
    person, diff = await ContactService.update_person(db, org_id, contact_id, person_id, data)
    if diff:
        await AuditService.log(
            db=db,
            action="CONTACT_PERSON_UPDATED",
            resource_type="contact",
            resource_id=str(contact_id),
            organisation_id=org_id,
            user_id=current_user.id,
            diff=diff,
            request=request,
        )
    return person


@router.delete(
    "/{contact_id}/people/{person_id}",
    status_code=204,
    dependencies=[Depends(require_permission("contact", "update"))],
)
async def delete_contact_person(
    org_id: uuid.UUID,
    contact_id: uuid.UUID,
    person_id: uuid.UUID,
    membership: OrgMembership,
    current_user: CurrentUser,
    db: DBSession,
    request: Request,
):
    await ContactService.delete_person(db, org_id, contact_id, person_id)
    await AuditService.log(
        db=db,
        action="CONTACT_PERSON_DELETED",
        resource_type="contact",
        resource_id=str(contact_id),
        organisation_id=org_id,
        user_id=current_user.id,
        diff={"person_id": str(person_id)},
        request=request,
    )


# ─── Contact Addresses ───────────────────────────────────────
@router.post(
    "/{contact_id}/addresses",
    response_model=ContactAddressResponse,
    status_code=201,
    dependencies=[Depends(require_permission("contact", "update"))],
)
async def add_contact_address(
    org_id: uuid.UUID,
    contact_id: uuid.UUID,
    data: ContactAddressCreate,
    membership: OrgMembership,
    current_user: CurrentUser,
    db: DBSession,
    request: Request,
):
    address = await ContactService.add_address(db, org_id, contact_id, data)
    await AuditService.log(
        db=db,
        action="ADDRESS_ADDED",
        resource_type="contact",
        resource_id=str(contact_id),
        organisation_id=org_id,
        user_id=current_user.id,
        diff={"type": address.address_type.value, "line1": address.line1, "city": address.city},
        request=request,
    )
    return address


@router.patch(
    "/{contact_id}/addresses/{address_id}",
    response_model=ContactAddressResponse,
    dependencies=[Depends(require_permission("contact", "update"))],
)
async def update_contact_address(
    org_id: uuid.UUID,
    contact_id: uuid.UUID,
    address_id: uuid.UUID,
    data: ContactAddressUpdate,
    membership: OrgMembership,
    current_user: CurrentUser,
    db: DBSession,
    request: Request,
):
    address, diff = await ContactService.update_address(db, org_id, contact_id, address_id, data)
    if diff:
        await AuditService.log(
            db=db,
            action="ADDRESS_UPDATED",
            resource_type="contact",
            resource_id=str(contact_id),
            organisation_id=org_id,
            user_id=current_user.id,
            diff=diff,
            request=request,
        )
    return address


@router.delete(
    "/{contact_id}/addresses/{address_id}",
    status_code=204,
    dependencies=[Depends(require_permission("contact", "update"))],
)
async def delete_contact_address(
    org_id: uuid.UUID,
    contact_id: uuid.UUID,
    address_id: uuid.UUID,
    membership: OrgMembership,
    current_user: CurrentUser,
    db: DBSession,
    request: Request,
):
    await ContactService.delete_address(db, org_id, contact_id, address_id)
    await AuditService.log(
        db=db,
        action="ADDRESS_DELETED",
        resource_type="contact",
        resource_id=str(contact_id),
        organisation_id=org_id,
        user_id=current_user.id,
        diff={"address_id": str(address_id)},
        request=request,
    )


# ─── Contact Notes ───────────────────────────────────────────
@router.get(
    "/{contact_id}/notes",
    response_model=list[ContactNoteResponse],
    dependencies=[Depends(require_permission("contact_note", "read"))],
)
async def list_contact_notes(
    org_id: uuid.UUID,
    contact_id: uuid.UUID,
    membership: OrgMembership,
    db: DBSession,
):
    return await ContactService.list_notes(db, org_id, contact_id)


@router.post(
    "/{contact_id}/notes",
    response_model=ContactNoteResponse,
    status_code=201,
    dependencies=[Depends(require_permission("contact_note", "create"))],
)
async def add_contact_note(
    org_id: uuid.UUID,
    contact_id: uuid.UUID,
    data: ContactNoteCreate,
    membership: OrgMembership,
    current_user: CurrentUser,
    db: DBSession,
    request: Request,
):
    note = await ContactService.add_note(db, org_id, contact_id, data.content, current_user.id)
    await AuditService.log(
        db=db,
        action="CONTACT_NOTE_ADDED",
        resource_type="contact",
        resource_id=str(contact_id),
        organisation_id=org_id,
        user_id=current_user.id,
        request=request,
    )
    return ContactNoteResponse(
        id=note.id,
        contact_id=note.contact_id,
        organisation_id=note.organisation_id,
        content=note.content,
        created_by_id=current_user.id,
        created_by_name=current_user.full_name or current_user.email,
        created_at=note.created_at,
    )


# ─── Contact Documents ───────────────────────────────────────
@router.get(
    "/{contact_id}/documents",
    response_model=list[ContactDocumentResponse],
    dependencies=[Depends(require_permission("contact_document", "read"))],
)
async def list_contact_documents(
    org_id: uuid.UUID,
    contact_id: uuid.UUID,
    membership: OrgMembership,
    db: DBSession,
):
    return await ContactService.list_documents(db, org_id, contact_id)


@router.post(
    "/{contact_id}/documents",
    response_model=ContactDocumentResponse,
    status_code=201,
    dependencies=[Depends(require_permission("contact_document", "attach"))],
)
async def attach_contact_document(
    org_id: uuid.UUID,
    contact_id: uuid.UUID,
    data: ContactDocumentAttach,
    membership: OrgMembership,
    current_user: CurrentUser,
    db: DBSession,
    request: Request,
):
    doc = await ContactService.attach_document(
        db=db, org_id=org_id, contact_id=contact_id, file_id=data.file_id, user_id=current_user.id
    )
    await AuditService.log(
        db=db,
        action="CONTACT_DOCUMENT_ATTACHED",
        resource_type="contact",
        resource_id=str(contact_id),
        organisation_id=org_id,
        user_id=current_user.id,
        diff={"file_id": str(data.file_id), "filename": doc.filename},
        request=request,
    )
    return doc
