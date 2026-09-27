"""
Warp Ladger — Smart Document Capture Router
REST endpoints for invoice & receipt uploads, processing, review, and draft bill generation.
"""
import math
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File as FastAPIFile,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.audit.service import AuditService
from app.bills.schemas import BillDetailResponse
from app.core.config import settings
from app.core.dependencies import (
    CurrentUser,
    DBSession,
    OrgMembership,
    require_permission,
)
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.database.models import (
    CapturedDocument,
    Contact,
    DocumentExtraction,
    DocumentExtractionField,
    DocumentExtractionLine,
    DocumentProcessingJob,
    DocumentProcessingStatus,
    DocumentType,
    File,
)
from app.documents.schemas import (
    BulkFieldCorrectionRequest,
    CapturedDocumentResponse,
    ClassificationOverrideRequest,
    CreateBillFromExtractionRequest,
    DocumentExtractionFieldResponse,
    DocumentExtractionLineResponse,
    DocumentExtractionResponse,
    DocumentInboxSummary,
    DocumentListResponse,
    DuplicateCheckResponse,
    DuplicateOverrideRequest,
    FieldCorrectionRequest,
    MathValidationResponse,
    SingleFieldCorrectionRequest,
    SupplierMatchResponse,
    get_confidence_level,
)
from app.documents.services.conversion_service import DocumentConversionService
from app.documents.services.duplicate_service import DocumentDuplicateService
from app.documents.services.matching_service import SupplierMatchingService
from app.documents.services.processing_service import DocumentProcessingService
from app.documents.services.security_service import DocumentSecurityService
from app.documents.services.validation_service import DocumentValidationService
from app.files.storage import get_storage_backend, make_storage_key

router = APIRouter()


# ─── 1. Upload & Intake Document ──────────────────────────────
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CapturedDocumentResponse,
    dependencies=[Depends(require_permission("documents", "process"))],
)
@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    response_model=CapturedDocumentResponse,
    dependencies=[Depends(require_permission("documents", "process"))],
)
async def upload_document(
    org_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
    membership: OrgMembership,
    background_tasks: BackgroundTasks,
    upload: Optional[UploadFile] = FastAPIFile(default=None),
    file: Optional[UploadFile] = FastAPIFile(default=None),
    auto_process: bool = Query(default=True),
):
    """
    Upload an invoice/receipt image or PDF.
    Validates binary header, enforces limits, computes SHA-256, stores privately,
    and queues for AI extraction.
    """
    actual_file = upload or file
    if not actual_file:
        raise BadRequestError("File upload is required.", code="FILE_REQUIRED")

    data = await actual_file.read()
    filename = DocumentSecurityService.sanitize_filename(actual_file.filename or "invoice.pdf")

    # Inspect magic bytes and validate size
    verified_mime, sha256_checksum, size_bytes = DocumentSecurityService.validate_file(
        data=data,
        filename=filename,
        content_type=actual_file.content_type,
    )

    # Store in object storage
    storage = get_storage_backend()
    storage_key = make_storage_key(org_id, filename)
    await storage.upload(key=storage_key, data=data, content_type=verified_mime)

    # Create platform File record
    file_record = File(
        organisation_id=org_id,
        uploaded_by_id=current_user.id,
        bucket=settings.STORAGE_BUCKET_NAME,
        key=storage_key,
        filename=filename,
        content_type=verified_mime,
        size_bytes=size_bytes,
    )
    db.add(file_record)
    await db.flush()

    # Create CapturedDocument record
    captured_doc = CapturedDocument(
        organisation_id=org_id,
        file_id=file_record.id,
        original_filename=filename,
        mime_type=verified_mime,
        file_size_bytes=size_bytes,
        checksum_sha256=sha256_checksum,
        processing_status=DocumentProcessingStatus.QUEUED,
        created_by_id=current_user.id,
    )
    db.add(captured_doc)
    await db.flush()

    await AuditService.log_static(
        db=db,
        action="DOCUMENT_UPLOADED",
        resource_type="captured_document",
        resource_id=str(captured_doc.id),
        organisation_id=org_id,
        user_id=current_user.id,
        diff={"filename": filename, "checksum": sha256_checksum, "size": size_bytes},
    )

    # Run processing (in testing/local dev, run immediately to populate extraction)
    if auto_process:
        await DocumentProcessingService.process_document(
            db=db,
            org_id=org_id,
            document_id=captured_doc.id,
            user_id=current_user.id,
        )

    url = await storage.generate_presigned_url(key=storage_key)
    return CapturedDocumentResponse(
        id=captured_doc.id,
        organisation_id=captured_doc.organisation_id,
        file_id=captured_doc.file_id,
        original_filename=captured_doc.original_filename,
        mime_type=captured_doc.mime_type,
        file_size_bytes=captured_doc.file_size_bytes,
        checksum_sha256=captured_doc.checksum_sha256,
        page_count=captured_doc.page_count,
        processing_status=captured_doc.processing_status,
        document_type=captured_doc.document_type,
        document_type_confidence=captured_doc.document_type_confidence,
        current_extraction_id=captured_doc.current_extraction_id,
        created_bill_id=captured_doc.created_bill_id,
        user_document_type_override=captured_doc.user_document_type_override,
        file_url=url,
        created_at=captured_doc.created_at,
        updated_at=captured_doc.updated_at,
    )


# ─── 2. Document Inbox List ──────────────────────────────────
@router.get(
    "",
    response_model=DocumentListResponse,
    dependencies=[Depends(require_permission("documents", "read"))],
)
async def list_documents(
    org_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """
    Document Inbox: Lists captured documents with filtering by status and search terms.
    """
    query = (
        select(CapturedDocument)
        .where(CapturedDocument.organisation_id == org_id)
        .order_by(CapturedDocument.created_at.desc())
    )

    if status_filter:
        s_upper = status_filter.upper()
        if s_upper == "NEEDS_REVIEW":
            query = query.where(
                CapturedDocument.processing_status.in_(
                    [
                        DocumentProcessingStatus.NEEDS_MANUAL_REVIEW,
                        DocumentProcessingStatus.DUPLICATE_FILE,
                    ]
                )
            )
        elif s_upper == "READY":
            query = query.where(
                CapturedDocument.processing_status == DocumentProcessingStatus.READY_FOR_REVIEW
            )
        elif s_upper == "PROCESSING":
            query = query.where(
                CapturedDocument.processing_status.in_(
                    [
                        DocumentProcessingStatus.QUEUED,
                        DocumentProcessingStatus.PROCESSING,
                        DocumentProcessingStatus.EXTRACTING,
                        DocumentProcessingStatus.VALIDATING,
                    ]
                )
            )
        elif s_upper == "COMPLETED":
            query = query.where(
                CapturedDocument.processing_status.in_(
                    [
                        DocumentProcessingStatus.CONVERTED_TO_BILL,
                        DocumentProcessingStatus.PROCESSED_RECEIPT,
                    ]
                )
            )
        elif s_upper == "FAILED":
            query = query.where(
                CapturedDocument.processing_status == DocumentProcessingStatus.FAILED
            )
        elif hasattr(DocumentProcessingStatus, s_upper):
            query = query.where(
                CapturedDocument.processing_status == DocumentProcessingStatus[s_upper]
            )

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                CapturedDocument.original_filename.ilike(search_pattern),
            )
        )

    # Count total
    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    documents = result.scalars().all()

    # Load associated extractions and bills for rich inbox cards
    storage = get_storage_backend()
    items: list[CapturedDocumentResponse] = []

    for doc in documents:
        supp_name = None
        inv_num = None
        tot = None
        curr = "GBP"

        if doc.current_extraction_id:
            ext_res = await db.execute(
                select(DocumentExtraction).where(DocumentExtraction.id == doc.current_extraction_id)
            )
            ext = ext_res.scalar_one_or_none()
            if ext:
                supp_name = ext.supplier_name_normalized or ext.supplier_name_raw
                inv_num = ext.invoice_number
                tot = ext.total
                curr = ext.currency or "GBP"

        # Resolve created bill number if any
        bill_num = None
        if doc.created_bill_id:
            from app.database.models import Bill
            b_res = await db.execute(select(Bill).where(Bill.id == doc.created_bill_id))
            b = b_res.scalar_one_or_none()
            if b:
                bill_num = b.internal_bill_number or b.supplier_invoice_number

        items.append(
            CapturedDocumentResponse(
                id=doc.id,
                organisation_id=doc.organisation_id,
                file_id=doc.file_id,
                original_filename=doc.original_filename,
                mime_type=doc.mime_type,
                file_size_bytes=doc.file_size_bytes,
                checksum_sha256=doc.checksum_sha256,
                page_count=doc.page_count,
                processing_status=doc.processing_status,
                document_type=doc.document_type,
                document_type_confidence=doc.document_type_confidence,
                current_extraction_id=doc.current_extraction_id,
                created_bill_id=doc.created_bill_id,
                created_bill_number=bill_num,
                user_document_type_override=doc.user_document_type_override,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                supplier_name=supp_name,
                invoice_number=inv_num,
                total=tot,
                currency=curr,
            )
        )

    total_pages = max(1, math.ceil(total / page_size))
    return DocumentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ─── 3. Document Inbox Summary Metrics ───────────────────────
@router.get(
    "/summary",
    response_model=DocumentInboxSummary,
    dependencies=[Depends(require_permission("documents", "read"))],
)
async def get_document_inbox_summary(
    org_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
):
    """Returns status metrics for inbox filtering badges."""
    query = (
        select(
            CapturedDocument.processing_status,
            func.count(CapturedDocument.id),
        )
        .where(CapturedDocument.organisation_id == org_id)
        .group_by(CapturedDocument.processing_status)
    )
    res = await db.execute(query)
    counts = dict(res.all())

    needs_review = counts.get(DocumentProcessingStatus.NEEDS_MANUAL_REVIEW, 0) + counts.get(
        DocumentProcessingStatus.DUPLICATE_FILE, 0
    )
    processing = (
        counts.get(DocumentProcessingStatus.QUEUED, 0)
        + counts.get(DocumentProcessingStatus.PROCESSING, 0)
        + counts.get(DocumentProcessingStatus.EXTRACTING, 0)
        + counts.get(DocumentProcessingStatus.VALIDATING, 0)
    )
    ready = counts.get(DocumentProcessingStatus.READY_FOR_REVIEW, 0)
    completed = counts.get(DocumentProcessingStatus.CONVERTED_TO_BILL, 0) + counts.get(
        DocumentProcessingStatus.PROCESSED_RECEIPT, 0
    )
    failed = counts.get(DocumentProcessingStatus.FAILED, 0)
    total = sum(counts.values())

    return DocumentInboxSummary(
        total_documents=total,
        needs_review_count=needs_review,
        processing_count=processing,
        ready_count=ready,
        completed_count=completed,
        failed_count=failed,
    )


async def _build_extraction_response(
    db: AsyncSession,
    org_id: uuid.UUID,
    extraction_id: uuid.UUID,
) -> Optional[DocumentExtractionResponse]:
    """Helper to load structured extraction data, lines, fields, and validations."""
    ext_res = await db.execute(
        select(DocumentExtraction)
        .where(DocumentExtraction.id == extraction_id)
        .where(DocumentExtraction.organisation_id == org_id)
        .options(
            selectinload(DocumentExtraction.fields),
            selectinload(DocumentExtraction.lines),
        )
    )
    ext = ext_res.scalar_one_or_none()
    if not ext:
        return None

    # Convert fields
    field_responses: list[DocumentExtractionFieldResponse] = [
        DocumentExtractionFieldResponse(
            id=f.id,
            extraction_id=f.extraction_id,
            field_name=f.field_name,
            raw_value=f.raw_value,
            normalized_value=f.normalized_value,
            confidence=f.confidence,
            confidence_level=get_confidence_level(f.confidence),
            page_number=f.page_number,
            bounding_box=f.bounding_box,
            source_text=f.source_text,
            manually_corrected=f.manually_corrected,
            original_value=f.original_value,
            corrected_by_id=f.corrected_by_id,
            corrected_at=f.corrected_at,
        )
        for f in ext.fields
    ]

    # Convert lines
    line_responses: list[DocumentExtractionLineResponse] = [
        DocumentExtractionLineResponse(
            id=l.id,
            extraction_id=l.extraction_id,
            position=l.position,
            description=l.description,
            quantity=l.quantity,
            unit_price=l.unit_price,
            net_amount=l.net_amount,
            tax_rate=l.tax_rate,
            tax_amount=l.tax_amount,
            gross_amount=l.gross_amount,
            confidence=l.confidence,
            confidence_level=get_confidence_level(l.confidence),
            page_number=l.page_number,
            manually_corrected=l.manually_corrected,
        )
        for l in ext.lines
    ]

    # Supplier match summary
    supp_match = None
    if ext.matched_supplier_id:
        from app.database.models import Contact
        c_res = await db.execute(select(Contact).where(Contact.id == ext.matched_supplier_id))
        cont = c_res.scalar_one_or_none()
        if cont:
            supp_match = SupplierMatchResponse(
                matched_supplier_id=cont.id,
                supplier_name=cont.business_name,
                vat_number=cont.vat_number,
                email=cont.email,
                confidence=ext.matched_supplier_confidence,
                match_reason=ext.supplier_match_reason,
                is_exact_match=(ext.matched_supplier_confidence == Decimal("1.00")),
            )

    # Math validation response
    math_val = DocumentValidationService.validate_totals(
        subtotal=ext.subtotal,
        discount_total=ext.discount_total,
        tax_total=ext.tax_total,
        total=ext.total,
    )
    fields_text = " ".join(f"{(f.source_text or '')} {(f.raw_value or '')}" for f in ext.fields)
    raw_text = f"{str(ext.raw_extraction or '')} {fields_text}"
    has_bank, bank_warn = DocumentValidationService.detect_bank_details(raw_text)
    math_val.has_bank_details = has_bank
    math_val.bank_details_warning = bank_warn

    # Duplicate check response
    dup_resp = None
    if ext.duplicate_severity:
        dup_resp = DuplicateCheckResponse(
            is_duplicate=True,
            severity=ext.duplicate_severity,
            duplicate_document_id=ext.duplicate_document_id,
            duplicate_bill_id=ext.duplicate_bill_id,
            reason="Duplicate invoice or document detected.",
        )

    return DocumentExtractionResponse(
        id=ext.id,
        organisation_id=ext.organisation_id,
        document_id=ext.document_id,
        provider=ext.provider,
        provider_model=ext.provider_model,
        schema_version=ext.schema_version,
        document_type=ext.document_type,
        document_type_confidence=ext.document_type_confidence,
        classification_level=get_confidence_level(ext.document_type_confidence),
        supplier_name_raw=ext.supplier_name_raw,
        supplier_name_normalized=ext.supplier_name_normalized,
        supplier_address_raw=ext.supplier_address_raw,
        supplier_email=ext.supplier_email,
        supplier_phone=ext.supplier_phone,
        supplier_vat_number=ext.supplier_vat_number,
        supplier_company_number=ext.supplier_company_number,
        invoice_number=ext.invoice_number,
        invoice_date=ext.invoice_date,
        due_date=ext.due_date,
        purchase_order_number=ext.purchase_order_number,
        reference=ext.reference,
        currency=ext.currency or "GBP",
        subtotal=ext.subtotal,
        discount_total=ext.discount_total,
        tax_total=ext.tax_total,
        total=ext.total,
        math_valid=ext.math_valid,
        math_validation_notes=ext.math_validation_notes,
        tax_valid=ext.tax_valid,
        date_valid=ext.date_valid,
        matched_supplier_id=ext.matched_supplier_id,
        matched_supplier_confidence=ext.matched_supplier_confidence,
        supplier_match_reason=ext.supplier_match_reason,
        duplicate_document_id=ext.duplicate_document_id,
        duplicate_bill_id=ext.duplicate_bill_id,
        duplicate_severity=ext.duplicate_severity,
        processing_started_at=ext.processing_started_at,
        processing_completed_at=ext.processing_completed_at,
        is_current=ext.is_current,
        created_at=ext.created_at,
        fields=field_responses,
        lines=line_responses,
        supplier_match=supp_match,
        math_validation=math_val,
        duplicate_check=dup_resp,
    )


# ─── 4. Get Document Details ─────────────────────────────────
@router.get(
    "/{document_id}",
    response_model=CapturedDocumentResponse,
    dependencies=[Depends(require_permission("documents", "read"))],
)
async def get_document(
    org_id: uuid.UUID,
    document_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
):
    """Retrieve document metadata and pre-signed view/download URL."""
    res = await db.execute(
        select(CapturedDocument)
        .where(CapturedDocument.id == document_id)
        .where(CapturedDocument.organisation_id == org_id)
    )
    doc = res.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Captured document not found in organisation.")

    # Generate pre-signed URL for viewing original document
    file_res = await db.execute(select(File).where(File.id == doc.file_id))
    file_rec = file_res.scalar_one_or_none()
    file_url = None
    if file_rec:
        storage = get_storage_backend()
        file_url = await storage.generate_presigned_url(key=file_rec.key)

    extraction = None
    extractions = []
    if doc.current_extraction_id:
        extraction = await _build_extraction_response(db, org_id, doc.current_extraction_id)
        if extraction:
            extractions = [extraction]

    return CapturedDocumentResponse(
        id=doc.id,
        organisation_id=doc.organisation_id,
        file_id=doc.file_id,
        original_filename=doc.original_filename,
        mime_type=doc.mime_type,
        file_size_bytes=doc.file_size_bytes,
        checksum_sha256=doc.checksum_sha256,
        page_count=doc.page_count,
        processing_status=doc.processing_status,
        document_type=doc.document_type,
        document_type_confidence=doc.document_type_confidence,
        current_extraction_id=doc.current_extraction_id,
        created_bill_id=doc.created_bill_id,
        user_document_type_override=doc.user_document_type_override,
        file_url=file_url,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        supplier_name=extraction.supplier_name_raw if extraction else None,
        invoice_number=extraction.invoice_number if extraction else None,
        total=extraction.total if extraction else None,
        currency=extraction.currency if extraction else None,
        extraction=extraction,
        extractions=extractions,
    )


# ─── 4b. Download Document ───────────────────────────────────
@router.get(
    "/{document_id}/download",
    dependencies=[Depends(require_permission("documents", "read"))],
)
async def download_document(
    org_id: uuid.UUID,
    document_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
):
    """Retrieve pre-signed download URL for a captured document."""
    res = await db.execute(
        select(CapturedDocument)
        .where(CapturedDocument.id == document_id)
        .where(CapturedDocument.organisation_id == org_id)
    )
    doc = res.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Captured document not found in organisation.")

    file_res = await db.execute(select(File).where(File.id == doc.file_id))
    file_rec = file_res.scalar_one_or_none()
    if not file_rec:
        raise NotFoundError("File record not found.")

    storage = get_storage_backend()
    file_url = await storage.generate_presigned_url(key=file_rec.key)
    return {"url": file_url}


# ─── 5. Trigger / Reprocess Document ─────────────────────────
@router.post(
    "/{document_id}/process",
    response_model=DocumentExtractionResponse,
    dependencies=[Depends(require_permission("documents", "process"))],
)
async def reprocess_document(
    org_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
    membership: OrgMembership,
):
    """Triggers or reprocesses document extraction."""
    ext = await DocumentProcessingService.process_document(
        db=db,
        org_id=org_id,
        document_id=document_id,
        user_id=current_user.id,
    )
    return await get_document_extraction(org_id, document_id, db, membership)


# ─── 6. Get Extraction Details (Review Screen) ───────────────
@router.get(
    "/{document_id}/extraction",
    response_model=DocumentExtractionResponse,
    dependencies=[Depends(require_permission("documents", "read"))],
)
async def get_document_extraction(
    org_id: uuid.UUID,
    document_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
):
    """
    Returns structured extraction result, field confidence values,
    provenance bounding boxes, line items, and verification status.
    """
    doc_res = await db.execute(
        select(CapturedDocument)
        .where(CapturedDocument.id == document_id)
        .where(CapturedDocument.organisation_id == org_id)
    )
    doc = doc_res.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Captured document not found in organisation.")

    if not doc.current_extraction_id:
        raise NotFoundError("Document has not yet completed extraction.")

    ext_resp = await _build_extraction_response(db, org_id, doc.current_extraction_id)
    if not ext_resp:
        raise NotFoundError("Extraction record not found.")

    return ext_resp


# ─── 7. Manually Correct Fields ──────────────────────────────
@router.patch(
    "/{document_id}/extraction",
    response_model=DocumentExtractionResponse,
    dependencies=[Depends(require_permission("documents", "correct"))],
)
async def correct_extraction_field(
    org_id: uuid.UUID,
    document_id: uuid.UUID,
    payload: BulkFieldCorrectionRequest,
    current_user: CurrentUser,
    db: DBSession,
    membership: OrgMembership,
):
    """
    Enables bookkeepers to correct incorrect AI extraction values.
    Preserves original values, tracks who made the change and when,
    and updates document verification states.
    """
    doc_res = await db.execute(
        select(CapturedDocument)
        .where(CapturedDocument.id == document_id)
        .where(CapturedDocument.organisation_id == org_id)
    )
    doc = doc_res.scalar_one_or_none()
    if not doc or not doc.current_extraction_id:
        raise NotFoundError("Captured document or extraction not found.")

    ext_res = await db.execute(
        select(DocumentExtraction)
        .where(DocumentExtraction.id == doc.current_extraction_id)
        .options(selectinload(DocumentExtraction.fields))
    )
    ext = ext_res.scalar_one_or_none()
    if not ext:
        raise NotFoundError("Extraction record not found.")

    now = datetime.now(UTC)

    for field_name, new_val in payload.corrections.items():
        # 1. Update DocumentExtractionField record if it exists
        field_rec = next((f for f in ext.fields if f.field_name == field_name), None)
        if field_rec:
            if not field_rec.manually_corrected:
                field_rec.original_value = field_rec.raw_value
            field_rec.raw_value = new_val
            field_rec.normalized_value = new_val
            field_rec.manually_corrected = True
            field_rec.corrected_by_id = current_user.id
            field_rec.corrected_at = now

        # 2. Update aggregate field on DocumentExtraction
        if field_name == "invoice_number":
            ext.invoice_number = new_val
        elif field_name == "supplier_name":
            ext.supplier_name_normalized = new_val
        elif field_name == "currency":
            ext.currency = new_val
        elif field_name == "subtotal" and new_val:
            ext.subtotal = Decimal(str(new_val).replace("£", "").replace(",", "").strip())
        elif field_name == "tax_total" and new_val:
            ext.tax_total = Decimal(str(new_val).replace("£", "").replace(",", "").strip())
        elif field_name == "total" and new_val:
            ext.total = Decimal(str(new_val).replace("£", "").replace(",", "").strip())
        elif field_name == "due_date" and new_val:
            try:
                ext.due_date = datetime.fromisoformat(new_val)
            except Exception:
                pass

        await AuditService.log_static(
            db=db,
            action="DOCUMENT_FIELD_CORRECTED",
            resource_type="captured_document",
            resource_id=str(doc.id),
            organisation_id=org_id,
            user_id=current_user.id,
            diff={"field": field_name, "new_value": new_val},
        )

    # Re-evaluate math validation after manual corrections
    math_val = DocumentValidationService.validate_totals(
        subtotal=ext.subtotal,
        discount_total=ext.discount_total,
        tax_total=ext.tax_total,
        total=ext.total,
    )
    ext.math_valid = math_val.is_valid
    ext.math_validation_notes = math_val.notes

    if ext.math_valid and doc.processing_status == DocumentProcessingStatus.NEEDS_MANUAL_REVIEW:
        doc.processing_status = DocumentProcessingStatus.READY_FOR_REVIEW

    await db.flush()
    return await get_document_extraction(org_id, document_id, db, membership)


@router.patch(
    "/{document_id}/fields/{field_id}",
    response_model=DocumentExtractionFieldResponse,
    dependencies=[Depends(require_permission("documents", "correct"))],
)
async def correct_single_extraction_field(
    org_id: uuid.UUID,
    document_id: uuid.UUID,
    field_id: uuid.UUID,
    payload: SingleFieldCorrectionRequest,
    current_user: CurrentUser,
    db: DBSession,
    membership: OrgMembership,
):
    """
    Enables bookkeepers to correct an individual AI extraction field by ID.
    Preserves original values, tracks who made the change and when.
    """
    doc_res = await db.execute(
        select(CapturedDocument)
        .where(CapturedDocument.id == document_id)
        .where(CapturedDocument.organisation_id == org_id)
    )
    doc = doc_res.scalar_one_or_none()
    if not doc or not doc.current_extraction_id:
        raise NotFoundError("Captured document or extraction not found.")

    ext_res = await db.execute(
        select(DocumentExtraction)
        .where(DocumentExtraction.id == doc.current_extraction_id)
        .options(selectinload(DocumentExtraction.fields))
    )
    ext = ext_res.scalar_one_or_none()
    if not ext:
        raise NotFoundError("Extraction record not found.")

    field_rec = next((f for f in ext.fields if f.id == field_id), None)
    if not field_rec:
        raise NotFoundError("Extraction field not found.")

    now = datetime.now(UTC)
    new_val = payload.value or ""
    if not field_rec.manually_corrected:
        field_rec.original_value = field_rec.raw_value
    field_rec.raw_value = new_val
    field_rec.normalized_value = new_val
    field_rec.manually_corrected = True
    field_rec.corrected_by_id = current_user.id
    field_rec.corrected_at = now

    field_name = field_rec.field_name
    if field_name == "invoice_number":
        ext.invoice_number = new_val
    elif field_name == "supplier_name":
        ext.supplier_name_normalized = new_val
    elif field_name == "currency":
        ext.currency = new_val
    elif field_name == "subtotal" and new_val:
        ext.subtotal = Decimal(str(new_val).replace("£", "").replace(",", "").strip())
    elif field_name == "tax_total" and new_val:
        ext.tax_total = Decimal(str(new_val).replace("£", "").replace(",", "").strip())
    elif field_name == "total" and new_val:
        ext.total = Decimal(str(new_val).replace("£", "").replace(",", "").strip())

    await AuditService.log_static(
        db=db,
        action="DOCUMENT_FIELD_CORRECTED",
        resource_type="captured_document",
        resource_id=str(doc.id),
        organisation_id=org_id,
        user_id=current_user.id,
        diff={"field": field_name, "new_value": new_val},
    )

    math_val = DocumentValidationService.validate_totals(
        subtotal=ext.subtotal,
        discount_total=ext.discount_total,
        tax_total=ext.tax_total,
        total=ext.total,
    )
    ext.math_valid = math_val.is_valid
    ext.math_validation_notes = math_val.notes

    if ext.math_valid and doc.processing_status == DocumentProcessingStatus.NEEDS_MANUAL_REVIEW:
        doc.processing_status = DocumentProcessingStatus.READY_FOR_REVIEW

    await db.flush()
    return DocumentExtractionFieldResponse.model_validate(field_rec)


# ─── 8. Override Classification ───────────────────────────────
@router.patch(
    "/{document_id}/classification",
    response_model=CapturedDocumentResponse,
    dependencies=[Depends(require_permission("documents", "correct"))],
)
async def override_document_classification(
    org_id: uuid.UUID,
    document_id: uuid.UUID,
    payload: ClassificationOverrideRequest,
    current_user: CurrentUser,
    db: DBSession,
    membership: OrgMembership,
):
    """Allows user to manually change document classification."""
    res = await db.execute(
        select(CapturedDocument)
        .where(CapturedDocument.id == document_id)
        .where(CapturedDocument.organisation_id == org_id)
    )
    doc = res.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Captured document not found.")

    doc.user_document_type_override = payload.document_type
    doc.document_type = payload.document_type

    if payload.document_type == DocumentType.RECEIPT:
        doc.processing_status = DocumentProcessingStatus.PROCESSED_RECEIPT
    elif doc.processing_status == DocumentProcessingStatus.NEEDS_MANUAL_REVIEW:
        doc.processing_status = DocumentProcessingStatus.READY_FOR_REVIEW

    await AuditService.log_static(
        db=db,
        action="DOCUMENT_CLASSIFIED",
        resource_type="captured_document",
        resource_id=str(doc.id),
        organisation_id=org_id,
        user_id=current_user.id,
        diff={"override_type": payload.document_type.value},
    )
    await db.flush()
    return await get_document(org_id, document_id, db, membership)


# ─── 9. Create Phase 4 Draft Bill ────────────────────────────
@router.post(
    "/{document_id}/create-bill",
    status_code=status.HTTP_201_CREATED,
    response_model=BillDetailResponse,
    dependencies=[Depends(require_permission("documents", "create_bill"))],
)
async def create_bill_from_extraction(
    org_id: uuid.UUID,
    document_id: uuid.UUID,
    payload: CreateBillFromExtractionRequest,
    current_user: CurrentUser,
    db: DBSession,
    membership: OrgMembership,
):
    """
    Automates Phase 4: converts the extracted document into a Draft Bill.
    Idempotent: double-clicks return the existing bill.
    Links the original document and preserves full audit history.
    """
    bill = await DocumentConversionService.convert_to_draft_bill(
        db=db,
        org_id=org_id,
        document_id=document_id,
        user_id=current_user.id,
        request=payload,
    )
    from app.bills.service import BillService
    return await BillService.get_bill(db, org_id, bill.id)


# ─── 10. Retry Document Extraction ───────────────────────────
@router.post(
    "/{document_id}/retry",
    response_model=CapturedDocumentResponse,
    dependencies=[Depends(require_permission("documents", "retry"))],
)
async def retry_document(
    org_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
    membership: OrgMembership,
):
    """Retries a failed or stalled document processing task."""
    res = await db.execute(
        select(CapturedDocument)
        .where(CapturedDocument.id == document_id)
        .where(CapturedDocument.organisation_id == org_id)
    )
    doc = res.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Captured document not found.")

    doc.processing_status = DocumentProcessingStatus.QUEUED
    await db.flush()

    await DocumentProcessingService.process_document(
        db=db,
        org_id=org_id,
        document_id=doc.id,
        user_id=current_user.id,
    )
    return await get_document(org_id, document_id, db, membership)


# ─── 11. Discard Document ─────────────────────────────────────
@router.post(
    "/{document_id}/discard",
    response_model=CapturedDocumentResponse,
    dependencies=[Depends(require_permission("documents", "discard"))],
)
async def discard_document(
    org_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
    membership: OrgMembership,
):
    """Marks a captured document as DISCARDED."""
    res = await db.execute(
        select(CapturedDocument)
        .where(CapturedDocument.id == document_id)
        .where(CapturedDocument.organisation_id == org_id)
    )
    doc = res.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Captured document not found.")

    if doc.created_bill_id:
        raise ConflictError("Cannot discard a document that has already been converted to a bill.")

    doc.processing_status = DocumentProcessingStatus.DISCARDED
    await AuditService.log_static(
        db=db,
        action="DOCUMENT_DISCARDED",
        resource_type="captured_document",
        resource_id=str(doc.id),
        organisation_id=org_id,
        user_id=current_user.id,
    )
    await db.flush()
    return await get_document(org_id, document_id, db, membership)


# ─── 12. Duplicate Override ───────────────────────────────────
@router.post(
    "/{document_id}/override-duplicate",
    response_model=CapturedDocumentResponse,
    dependencies=[Depends(require_permission("documents", "duplicate_override"))],
)
async def override_duplicate(
    org_id: uuid.UUID,
    document_id: uuid.UUID,
    payload: DuplicateOverrideRequest,
    current_user: CurrentUser,
    db: DBSession,
    membership: OrgMembership,
):
    """Allows an authorized user to override duplicate file or invoice warnings."""
    res = await db.execute(
        select(CapturedDocument)
        .where(CapturedDocument.id == document_id)
        .where(CapturedDocument.organisation_id == org_id)
    )
    doc = res.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Captured document not found.")

    doc.processing_status = DocumentProcessingStatus.READY_FOR_REVIEW

    await AuditService.log_static(
        db=db,
        action="DOCUMENT_DUPLICATE_OVERRIDE",
        resource_type="captured_document",
        resource_id=str(doc.id),
        organisation_id=org_id,
        user_id=current_user.id,
        diff={"reason": payload.reason},
    )
    await db.flush()
    return await get_document(org_id, document_id, db, membership)
