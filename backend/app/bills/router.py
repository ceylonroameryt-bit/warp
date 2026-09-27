"""
Warp Ladger — Supplier Bills API Router (Phase 4)
Full REST implementation for supplier bills payables lifecycle.
All endpoints enforce multi-tenant isolation and role-based permissions.
"""
import hashlib
from typing import Optional
import uuid

import structlog
from fastapi import APIRouter, Depends, File as FastAPIFile, Form, HTTPException, Query, Response, UploadFile, status

from app.bills.duplicate_service import DuplicateBillService
from app.bills.schemas import (
    BillApproveRequest,
    BillCreate,
    BillDetailResponse,
    BillDocumentResponse,
    BillFilters,
    BillListResponse,
    BillRejectRequest,
    BillResponse,
    BillSubmitRequest,
    BillUpdate,
    BillVoidRequest,
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    PurchasesMetricsResponse,
)
from app.bills.service import BillService
from app.core.config import settings
from app.core.dependencies import CurrentUser, DBSession, OrgMembership, require_permission
from app.database.models import File
from app.files.storage import get_storage_backend, make_storage_key

log = structlog.get_logger(__name__)

router = APIRouter()


def _format_bill_detail(bill) -> BillDetailResponse:
    """Format a Bill ORM instance into BillDetailResponse with effective status and file details."""
    storage = get_storage_backend()
    resp = BillDetailResponse.model_validate(bill)
    resp.effective_status = BillService._effective_status(bill)

    # Format documents with filename and presigned URL if available
    doc_responses = []
    for doc in bill.documents:
        d_resp = BillDocumentResponse(
            id=doc.id,
            bill_id=doc.bill_id,
            file_id=doc.file_id,
            document_type=doc.document_type,
            checksum_sha256=doc.checksum_sha256,
            filename=doc.file.filename if doc.file else "unknown",
            content_type=doc.file.content_type if doc.file else "application/octet-stream",
            download_url=f"/api/v1/organisations/{bill.organisation_id}/bills/{bill.id}/documents/{doc.id}/download",
            created_at=doc.created_at,
        )
        doc_responses.append(d_resp)
    resp.documents = doc_responses

    # Format actor name in approval events if loaded
    for ev, ev_orm in zip(resp.approval_events, bill.approval_events):
        if ev_orm.actor:
            ev.actor_name = ev_orm.actor.full_name or ev_orm.actor.email

    return resp


# ─── List Bills ──────────────────────────────────────────────
@router.get("", response_model=BillListResponse, dependencies=[Depends(require_permission("bills", "read"))])
@router.get("/", response_model=BillListResponse, include_in_schema=False, dependencies=[Depends(require_permission("bills", "read"))])
async def list_bills(
    org_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    supplier_id: Optional[uuid.UUID] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    due_date_from: Optional[str] = Query(default=None),
    due_date_to: Optional[str] = Query(default=None),
    currency: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort_by: str = Query(default="bill_date"),
    sort_dir: str = Query(default="desc"),
):
    """List supplier bills with pagination, filtering, search, and dynamic OVERDUE status."""
    filters = BillFilters(
        status=status_filter,
        supplier_id=supplier_id,
        date_from=date_from,
        date_to=date_to,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        currency=currency,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    result = await BillService.list_bills(db, org_id, filters)
    bills = result["items"]

    items = []
    for b in bills:
        resp = BillResponse.model_validate(b)
        resp.effective_status = BillService._effective_status(b)
        if b.supplier:
            resp.supplier_name_snapshot = b.supplier.business_name
            resp.supplier_email_snapshot = b.supplier.email
        items.append(resp)

    return BillListResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
    )


# ─── Purchases Dashboard Metrics ─────────────────────────────
@router.get("/metrics", response_model=PurchasesMetricsResponse, dependencies=[Depends(require_permission("bills", "read"))])
async def get_purchases_metrics(
    org_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
):
    """Fetch aggregated metrics for the purchases dashboard."""
    return await BillService.get_purchases_metrics(db, org_id)


# ─── Duplicate Check ─────────────────────────────────────────
@router.post("/check-duplicate", response_model=DuplicateCheckResponse, dependencies=[Depends(require_permission("bills", "read"))])
async def check_duplicate_bill(
    org_id: uuid.UUID,
    data: DuplicateCheckRequest,
    db: DBSession,
    membership: OrgMembership,
):
    """Check for duplicate bills using supplier invoice number, date, amount, and file checksum."""
    return await DuplicateBillService.check_duplicates(
        db=db,
        org_id=org_id,
        supplier_id=data.supplier_id,
        supplier_invoice_number=data.supplier_invoice_number,
        bill_date=data.bill_date,
        total=data.total,
        file_checksum=data.file_checksum,
        exclude_bill_id=data.exclude_bill_id,
    )


# ─── Create Draft Bill ───────────────────────────────────────
@router.post("", response_model=BillDetailResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("bills", "create"))])
@router.post("/", response_model=BillDetailResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False, dependencies=[Depends(require_permission("bills", "create"))])
async def create_bill(
    org_id: uuid.UUID,
    data: BillCreate,
    db: DBSession,
    current_user: CurrentUser,
    membership: OrgMembership,
):
    """Create a new DRAFT bill with backend recalculations and duplicate prevention."""
    bill = await BillService.create_draft(db, org_id, current_user.id, data)
    await db.commit()
    return _format_bill_detail(bill)


# ─── Get Bill Detail ─────────────────────────────────────────
@router.get("/{bill_id}", response_model=BillDetailResponse, dependencies=[Depends(require_permission("bills", "read"))])
async def get_bill(
    org_id: uuid.UUID,
    bill_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
):
    """Get a single bill with full lines, documents, and approval events."""
    bill = await BillService.get_bill(db, org_id, bill_id)
    return _format_bill_detail(bill)


# ─── Update Draft Bill ───────────────────────────────────────
@router.patch("/{bill_id}", response_model=BillDetailResponse, dependencies=[Depends(require_permission("bills", "update"))])
async def update_bill(
    org_id: uuid.UUID,
    bill_id: uuid.UUID,
    data: BillUpdate,
    db: DBSession,
    current_user: CurrentUser,
    membership: OrgMembership,
):
    """Update a DRAFT or REJECTED bill. Validates optimistic locking."""
    bill = await BillService.update_draft(db, org_id, bill_id, current_user.id, data)
    await db.commit()
    return _format_bill_detail(bill)


# ─── Delete Draft Bill ───────────────────────────────────────
@router.delete("/{bill_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("bills", "update"))])
async def delete_bill(
    org_id: uuid.UUID,
    bill_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    membership: OrgMembership,
):
    """Delete a DRAFT bill. Approved bills must be voided instead."""
    await BillService.delete_draft(db, org_id, bill_id, current_user.id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── Submit for Approval ─────────────────────────────────────
@router.post("/{bill_id}/submit", response_model=BillDetailResponse, dependencies=[Depends(require_permission("bills", "submit"))])
async def submit_bill(
    org_id: uuid.UUID,
    bill_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    membership: OrgMembership,
    request: BillSubmitRequest = BillSubmitRequest(),
):
    """Submit a DRAFT or REJECTED bill for approval."""
    bill = await BillService.submit_for_approval(db, org_id, bill_id, current_user.id, request.comment)
    await db.commit()
    return _format_bill_detail(bill)


# ─── Approve Bill ────────────────────────────────────────────
@router.post("/{bill_id}/approve", response_model=BillDetailResponse, dependencies=[Depends(require_permission("bills", "approve"))])
async def approve_bill(
    org_id: uuid.UUID,
    bill_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    membership: OrgMembership,
    request: BillApproveRequest = BillApproveRequest(),
):
    """Approve an AWAITING_APPROVAL bill. Creates immutable snapshot."""
    bill = await BillService.approve_bill(db, org_id, bill_id, current_user.id, request.comment)
    await db.commit()
    return _format_bill_detail(bill)


# ─── Reject Bill ─────────────────────────────────────────────
@router.post("/{bill_id}/reject", response_model=BillDetailResponse, dependencies=[Depends(require_permission("bills", "reject"))])
async def reject_bill(
    org_id: uuid.UUID,
    bill_id: uuid.UUID,
    data: BillRejectRequest,
    db: DBSession,
    current_user: CurrentUser,
    membership: OrgMembership,
):
    """Reject a bill awaiting approval. Rejection reason is mandatory."""
    bill = await BillService.reject_bill(db, org_id, bill_id, current_user.id, data.reason)
    await db.commit()
    return _format_bill_detail(bill)


# ─── Void Bill ───────────────────────────────────────────────
@router.post("/{bill_id}/void", response_model=BillDetailResponse, dependencies=[Depends(require_permission("bills", "void"))])
async def void_bill(
    org_id: uuid.UUID,
    bill_id: uuid.UUID,
    data: BillVoidRequest,
    db: DBSession,
    current_user: CurrentUser,
    membership: OrgMembership,
):
    """Void an approved bill. Reason is mandatory."""
    bill = await BillService.void_bill(db, org_id, bill_id, current_user.id, data.reason)
    await db.commit()
    return _format_bill_detail(bill)


# ─── Documents: Attach / Upload ──────────────────────────────
@router.post("/{bill_id}/documents", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("bills", "update"))])
async def attach_bill_document(
    org_id: uuid.UUID,
    bill_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    membership: OrgMembership,
    upload: Optional[UploadFile] = FastAPIFile(None),
    file_id: Optional[uuid.UUID] = Form(None),
    document_type: str = Form("ORIGINAL_INVOICE"),
):
    """
    Attach a supporting document or original supplier invoice.
    Accepts either an uploaded file (calculating SHA-256) or an existing file_id.
    """
    checksum_sha256 = None

    if upload is not None:
        # Read file bytes and compute SHA-256
        data = await upload.read()
        checksum_sha256 = hashlib.sha256(data).hexdigest()

        # Check for duplicate document in org
        storage = get_storage_backend()
        key = make_storage_key(org_id, upload.filename or "invoice.pdf")
        await storage.upload(key=key, data=data, content_type=upload.content_type)

        file_rec = File(
            organisation_id=org_id,
            uploaded_by_id=current_user.id,
            bucket=settings.STORAGE_BUCKET_NAME,
            key=key,
            filename=upload.filename or "unknown",
            content_type=upload.content_type or "application/octet-stream",
            size_bytes=len(data),
        )
        db.add(file_rec)
        await db.flush()
        target_file_id = file_rec.id
    elif file_id is not None:
        target_file_id = file_id
    else:
        raise HTTPException(status_code=400, detail="Either a file upload or file_id must be provided.")

    doc = await BillService.attach_document(
        db=db,
        org_id=org_id,
        bill_id=bill_id,
        user_id=current_user.id,
        file_id=target_file_id,
        document_type=document_type,
        checksum_sha256=checksum_sha256,
    )
    await db.commit()

    return {
        "id": str(doc.id),
        "bill_id": str(doc.bill_id),
        "file_id": str(doc.file_id),
        "document_type": doc.document_type,
        "checksum_sha256": doc.checksum_sha256,
    }


# ─── Documents: List Bill Documents ──────────────────────────
@router.get("/{bill_id}/documents", response_model=list[BillDocumentResponse], dependencies=[Depends(require_permission("bills", "read"))])
async def list_bill_documents(
    org_id: uuid.UUID,
    bill_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
):
    """Retrieve all supporting documents attached to a bill."""
    bill = await BillService.get_bill(db, org_id, bill_id)
    formatted = _format_bill_detail(bill)
    return formatted.documents


# ─── Documents: Delete Document Link ─────────────────────────
@router.delete("/{bill_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("bills", "update"))])
async def remove_bill_document(
    org_id: uuid.UUID,
    bill_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    membership: OrgMembership,
):
    """Remove a document link from a bill."""
    await BillService.remove_document(db, org_id, bill_id, doc_id, current_user.id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── Documents: Download / Presigned URL ─────────────────────
@router.get("/{bill_id}/documents/{doc_id}/download", dependencies=[Depends(require_permission("bills", "read"))])
async def download_bill_document(
    org_id: uuid.UUID,
    bill_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
):
    """Retrieve presigned URL for secure document access."""
    from fastapi.responses import RedirectResponse
    bill = await BillService.get_bill(db, org_id, bill_id)
    doc = next((d for d in bill.documents if d.id == doc_id), None)
    if not doc or not doc.file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    
    storage = get_storage_backend()
    url = await storage.generate_presigned_url(key=doc.file.key)
    return {"url": url, "filename": doc.file.filename, "content_type": doc.file.content_type}

