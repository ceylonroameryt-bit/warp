"""
Warp Ladger — Invoice & Tax Rate API Router
Full REST implementation for invoice lifecycle and tax rate management.
All endpoints enforce org membership + fine-grained permissions.
"""
import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.dependencies import CurrentUser, DBSession, OrgMembership, require_permission
from app.invoices.schemas import (
    InvoiceApproveRequest,
    InvoiceCreate,
    InvoiceDeliveryResponse,
    InvoiceDetailResponse,
    InvoiceFilters,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceSendRequest,
    InvoiceUpdate,
    InvoiceVoidRequest,
    TaxRateCreate,
    TaxRateResponse,
    TaxRateUpdate,
)
from app.invoices.service import InvoiceService
from app.invoices.tax_service import TaxRateService

log = structlog.get_logger(__name__)

router = APIRouter()
tax_router = APIRouter()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INVOICE ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/", response_model=InvoiceListResponse, dependencies=[Depends(require_permission("invoices", "read"))])
async def list_invoices(
    org_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    customer_id: Optional[uuid.UUID] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    currency: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc"),
):
    """List invoices with pagination, filtering, and search. OVERDUE derived at runtime."""
    filters = InvoiceFilters(
        status=status_filter,
        customer_id=customer_id,
        currency=currency,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    result = await InvoiceService.list_invoices(db, org_id, filters)
    invoices = result["items"]

    # Attach effective_status (includes OVERDUE derivation) to each response
    items = []
    for inv in invoices:
        resp = InvoiceResponse.model_validate(inv)
        resp.effective_status = InvoiceService._effective_status(inv)
        items.append(resp)

    return InvoiceListResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
    )


@router.post("/", response_model=InvoiceDetailResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("invoices", "create"))])
async def create_invoice(
    org_id: uuid.UUID,
    data: InvoiceCreate,
    db: DBSession,
    current_user: CurrentUser,
    membership: OrgMembership,
):
    """Create a new DRAFT invoice. Totals are recalculated server-side."""
    invoice = await InvoiceService.create_draft(db, org_id, current_user.id, data)
    await db.commit()
    invoice = await InvoiceService.get_invoice(db, org_id, invoice.id)
    resp = InvoiceDetailResponse.model_validate(invoice)
    resp.effective_status = InvoiceService._effective_status(invoice)
    return resp


@router.get("/{invoice_id}", response_model=InvoiceDetailResponse, dependencies=[Depends(require_permission("invoices", "read"))])
async def get_invoice(
    org_id: uuid.UUID,
    invoice_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
):
    """Get a single invoice with full line detail. Always org-scoped."""
    invoice = await InvoiceService.get_invoice(db, org_id, invoice_id)
    resp = InvoiceDetailResponse.model_validate(invoice)
    resp.effective_status = InvoiceService._effective_status(invoice)
    return resp


@router.patch("/{invoice_id}", response_model=InvoiceDetailResponse, dependencies=[Depends(require_permission("invoices", "update"))])
async def update_invoice(
    org_id: uuid.UUID,
    invoice_id: uuid.UUID,
    data: InvoiceUpdate,
    db: DBSession,
    current_user: CurrentUser,
    membership: OrgMembership,
):
    """Update a DRAFT invoice. Raises 400 if invoice is approved/sent/void."""
    invoice = await InvoiceService.update_draft(db, org_id, invoice_id, current_user.id, data)
    await db.commit()
    invoice = await InvoiceService.get_invoice(db, org_id, invoice.id)
    resp = InvoiceDetailResponse.model_validate(invoice)
    resp.effective_status = InvoiceService._effective_status(invoice)
    return resp


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("invoices", "update"))])
async def delete_invoice(
    org_id: uuid.UUID,
    invoice_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    membership: OrgMembership,
):
    """Delete a DRAFT invoice. Approved invoices must be voided."""
    await InvoiceService.delete_draft(db, org_id, invoice_id, current_user.id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{invoice_id}/approve", response_model=InvoiceDetailResponse, dependencies=[Depends(require_permission("invoices", "approve"))])
async def approve_invoice(
    org_id: uuid.UUID,
    invoice_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    membership: OrgMembership,
    request: InvoiceApproveRequest = InvoiceApproveRequest(),
):
    """
    Approve a DRAFT invoice.
    Assigns official invoice number, captures customer snapshot,
    verifies all calculations. Atomic transaction.
    """
    invoice = await InvoiceService.approve_invoice(db, org_id, invoice_id, current_user.id)
    await db.commit()
    invoice = await InvoiceService.get_invoice(db, org_id, invoice.id)
    resp = InvoiceDetailResponse.model_validate(invoice)
    resp.effective_status = InvoiceService._effective_status(invoice)
    return resp


@router.post("/{invoice_id}/void", response_model=InvoiceDetailResponse, dependencies=[Depends(require_permission("invoices", "void"))])
async def void_invoice(
    org_id: uuid.UUID,
    invoice_id: uuid.UUID,
    data: InvoiceVoidRequest,
    db: DBSession,
    current_user: CurrentUser,
    membership: OrgMembership,
):
    """Void an approved invoice. Reason is required. Invoice is retained for audit."""
    invoice = await InvoiceService.void_invoice(
        db, org_id, invoice_id, current_user.id, data.reason
    )
    await db.commit()
    invoice = await InvoiceService.get_invoice(db, org_id, invoice.id)
    resp = InvoiceDetailResponse.model_validate(invoice)
    resp.effective_status = InvoiceService._effective_status(invoice)
    return resp


@router.post("/{invoice_id}/send", response_model=InvoiceDeliveryResponse, dependencies=[Depends(require_permission("invoices", "send"))])
async def send_invoice(
    org_id: uuid.UUID,
    invoice_id: uuid.UUID,
    data: InvoiceSendRequest,
    db: DBSession,
    current_user: CurrentUser,
    membership: OrgMembership,
):
    """Queue invoice email delivery. Returns immediately; worker sends asynchronously."""
    from app.invoices.email_service import InvoiceEmailService

    delivery = await InvoiceEmailService.queue_send(
        db=db,
        org_id=org_id,
        invoice_id=invoice_id,
        send_request=data,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(delivery)
    return InvoiceDeliveryResponse.model_validate(delivery)


@router.post("/{invoice_id}/pdf", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_permission("invoices", "read"))])
async def generate_pdf(
    org_id: uuid.UUID,
    invoice_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    membership: OrgMembership,
):
    """Trigger PDF generation. Queues background job; returns job reference."""
    from app.invoices.pdf_service import PDFService

    try:
        file_link = await PDFService.generate_and_store(db, org_id, invoice_id)
        await db.commit()
        return {"status": "generated", "file_link_id": str(file_link.id)}
    except Exception as exc:
        log.error("pdf_generation_failed", exc=str(exc))
        raise HTTPException(status_code=500, detail="PDF generation failed.") from exc


@router.get("/{invoice_id}/pdf", dependencies=[Depends(require_permission("invoices", "read"))])
async def download_pdf(
    org_id: uuid.UUID,
    invoice_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
):
    """Download the generated invoice PDF (presigned URL or direct stream)."""
    from app.invoices.pdf_service import PDFService

    url = await PDFService.get_pdf_url(db, org_id, invoice_id)
    if not url:
        raise HTTPException(status_code=404, detail="PDF not yet generated. POST to /pdf first.")
    return {"download_url": url}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAX RATE ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@tax_router.get("/", response_model=list[TaxRateResponse], dependencies=[Depends(require_permission("invoices", "read"))])
async def list_tax_rates(
    org_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
    active_only: bool = Query(default=True),
):
    """List all tax rates for the organisation. Seeds defaults on first call."""
    return await TaxRateService.list_rates(db, org_id, active_only=active_only)


@tax_router.post("/", response_model=TaxRateResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("invoices", "update"))])
async def create_tax_rate(
    org_id: uuid.UUID,
    data: TaxRateCreate,
    db: DBSession,
    membership: OrgMembership,
):
    rate = await TaxRateService.create_rate(db, org_id, data)
    await db.commit()
    await db.refresh(rate)
    return rate


@tax_router.patch("/{tax_rate_id}", response_model=TaxRateResponse, dependencies=[Depends(require_permission("invoices", "update"))])
async def update_tax_rate(
    org_id: uuid.UUID,
    tax_rate_id: uuid.UUID,
    data: TaxRateUpdate,
    db: DBSession,
    membership: OrgMembership,
):
    rate = await TaxRateService.update_rate(db, org_id, tax_rate_id, data)
    await db.commit()
    await db.refresh(rate)
    return rate


@tax_router.delete("/{tax_rate_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("invoices", "update"))])
async def delete_tax_rate(
    org_id: uuid.UUID,
    tax_rate_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
):
    """Deactivates the tax rate (soft-delete). Historical invoice lines are preserved."""
    await TaxRateService.delete_rate(db, org_id, tax_rate_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
