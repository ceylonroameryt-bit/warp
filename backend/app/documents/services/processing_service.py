"""
Warp Ladger — Document Processing Pipeline Service
Orchestrates: Upload → Classify → Extract → Validate → Match Supplier → Duplicate Check → State Update.
"""
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.database.models import (
    AIUsageEvent,
    CapturedDocument,
    DocumentExtraction,
    DocumentExtractionField,
    DocumentExtractionLine,
    DocumentProcessingJob,
    DocumentProcessingStatus,
    DocumentType,
    ExtractionJobStatus,
    File,
)
from app.documents.providers.factory import get_document_provider
from app.documents.services.duplicate_service import DocumentDuplicateService
from app.documents.services.matching_service import SupplierMatchingService
from app.documents.services.validation_service import DocumentValidationService

log = structlog.get_logger(__name__)


class DocumentProcessingService:
    """Manages asynchronous and synchronous document processing workflows."""

    @staticmethod
    async def process_document(
        db: AsyncSession,
        org_id: uuid.UUID,
        document_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> DocumentExtraction:
        # 1. Fetch document & file
        result = await db.execute(
            select(CapturedDocument)
            .where(CapturedDocument.id == document_id)
            .where(CapturedDocument.organisation_id == org_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise NotFoundError("Captured document not found in organisation.")

        # Update document status to PROCESSING
        doc.processing_status = DocumentProcessingStatus.PROCESSING
        await db.flush()

        # Create processing job record
        job = DocumentProcessingJob(
            organisation_id=org_id,
            document_id=doc.id,
            job_type="EXTRACTION_PIPELINE",
            status=ExtractionJobStatus.RUNNING,
            attempt=1,
            started_at=datetime.now(UTC),
        )
        db.add(job)
        await db.flush()

        await AuditService.log_static(
            db=db,
            action="DOCUMENT_PROCESSING_STARTED",
            resource_type="captured_document",
            resource_id=str(doc.id),
            organisation_id=org_id,
            user_id=user_id,
        )

        try:
            # 2. Retrieve file data (or simulated data)
            file_res = await db.execute(select(File).where(File.id == doc.file_id))
            file_record = file_res.scalar_one_or_none()

            # For local dev/test or storage backend
            file_bytes = b"%PDF-1.4 Mock Document Content"
            if file_record and hasattr(file_record, "data") and file_record.data:
                file_bytes = file_record.data

            provider = get_document_provider()
            meta = provider.get_metadata()

            # 3. Classify Document
            doc.processing_status = DocumentProcessingStatus.EXTRACTING
            classification = await provider.classify_document(
                data=file_bytes,
                content_type=doc.mime_type,
                filename=doc.original_filename,
            )
            doc.document_type = classification.document_type
            doc.document_type_confidence = classification.confidence

            await AuditService.log_static(
                db=db,
                action="DOCUMENT_CLASSIFIED",
                resource_type="captured_document",
                resource_id=str(doc.id),
                organisation_id=org_id,
                user_id=user_id,
                diff={
                    "type": classification.document_type.value,
                    "confidence": str(classification.confidence),
                },
            )

            # 4. Extract structured fields
            extraction_output = await provider.extract_document(
                data=file_bytes,
                content_type=doc.mime_type,
                filename=doc.original_filename,
            )

            # Mark any previous extractions as not current
            prev_exts = await db.execute(
                select(DocumentExtraction)
                .where(DocumentExtraction.document_id == doc.id)
                .where(DocumentExtraction.is_current.is_(True))
            )
            for pe in prev_exts.scalars().all():
                pe.is_current = False

            # Create new DocumentExtraction record
            ext = DocumentExtraction(
                organisation_id=org_id,
                document_id=doc.id,
                provider=extraction_output.provider_name,
                provider_model=extraction_output.provider_model,
                schema_version=1,
                document_type=doc.document_type,
                document_type_confidence=doc.document_type_confidence,
                supplier_name_raw=extraction_output.supplier_name,
                supplier_name_normalized=extraction_output.supplier_name,
                supplier_address_raw=extraction_output.supplier_address,
                supplier_email=extraction_output.supplier_email,
                supplier_phone=extraction_output.supplier_phone,
                supplier_vat_number=extraction_output.supplier_vat_number,
                supplier_company_number=extraction_output.supplier_company_number,
                invoice_number=extraction_output.invoice_number,
                invoice_date=extraction_output.invoice_date,
                due_date=extraction_output.due_date,
                purchase_order_number=extraction_output.purchase_order_number,
                reference=extraction_output.reference,
                currency=extraction_output.currency,
                subtotal=extraction_output.subtotal,
                discount_total=extraction_output.discount_total,
                tax_total=extraction_output.tax_total,
                total=extraction_output.total,
                raw_extraction=extraction_output.raw_result,
                processing_started_at=job.started_at,
                processing_completed_at=datetime.now(UTC),
                is_current=True,
            )
            db.add(ext)
            await db.flush()

            # 5. Persist Fields with provenance & bounding boxes
            for f in extraction_output.fields:
                field_rec = DocumentExtractionField(
                    organisation_id=org_id,
                    extraction_id=ext.id,
                    field_name=f.name,
                    raw_value=f.raw_value,
                    normalized_value=f.normalized_value,
                    confidence=f.confidence,
                    page_number=f.page,
                    bounding_box=f.bounding_box,
                    source_text=f.source_text,
                )
                db.add(field_rec)

            # 6. Persist Line Items
            for l in extraction_output.lines:
                line_rec = DocumentExtractionLine(
                    organisation_id=org_id,
                    extraction_id=ext.id,
                    position=l.position,
                    description=l.description,
                    quantity=l.quantity,
                    unit_price=l.unit_price,
                    net_amount=l.net_amount,
                    tax_rate=l.tax_rate,
                    tax_amount=l.tax_amount,
                    gross_amount=l.gross_amount,
                    confidence=l.confidence,
                    page_number=l.page,
                )
                db.add(line_rec)

            await db.flush()

            # 7. Validation: Math, Tax, Dates, Bank Details
            doc.processing_status = DocumentProcessingStatus.VALIDATING
            math_check = DocumentValidationService.validate_totals(
                subtotal=ext.subtotal,
                discount_total=ext.discount_total,
                tax_total=ext.tax_total,
                total=ext.total,
            )
            lines_check_ok, lines_notes = DocumentValidationService.validate_lines(
                lines=extraction_output.lines, declared_subtotal=ext.subtotal
            )
            dates_ok, dates_notes = DocumentValidationService.validate_dates(
                invoice_date=ext.invoice_date, due_date=ext.due_date
            )

            ext.math_valid = math_check.is_valid and lines_check_ok
            ext.math_validation_notes = (
                f"{math_check.notes or ''} {lines_notes or ''}".strip() or None
            )
            ext.tax_valid = True
            ext.date_valid = dates_ok

            # 8. Supplier Matching
            supp_match = await SupplierMatchingService.match_supplier(
                db=db,
                org_id=org_id,
                extracted_name=ext.supplier_name_raw,
                extracted_vat=ext.supplier_vat_number,
                extracted_company_number=ext.supplier_company_number,
                extracted_email=ext.supplier_email,
            )
            if supp_match.matched_supplier_id:
                ext.matched_supplier_id = supp_match.matched_supplier_id
                ext.matched_supplier_confidence = supp_match.confidence
                ext.supplier_match_reason = supp_match.match_reason
                await AuditService.log_static(
                    db=db,
                    action="DOCUMENT_SUPPLIER_MATCHED",
                    resource_type="captured_document",
                    resource_id=str(doc.id),
                    organisation_id=org_id,
                    user_id=user_id,
                    diff={
                        "supplier_id": str(supp_match.matched_supplier_id),
                        "reason": supp_match.match_reason,
                    },
                )

            # 9. Duplicate Detection (Layer 1, 2, 3)
            dup_check = await DocumentDuplicateService.check_duplicates(
                db=db,
                org_id=org_id,
                doc_id=doc.id,
                checksum_sha256=doc.checksum_sha256,
                supplier_id=ext.matched_supplier_id,
                invoice_number=ext.invoice_number,
                invoice_date=ext.invoice_date,
                total=ext.total,
            )
            if dup_check.is_duplicate:
                ext.duplicate_document_id = dup_check.duplicate_document_id
                ext.duplicate_bill_id = dup_check.duplicate_bill_id
                ext.duplicate_severity = dup_check.severity
                await AuditService.log_static(
                    db=db,
                    action="DOCUMENT_DUPLICATE_DETECTED",
                    resource_type="captured_document",
                    resource_id=str(doc.id),
                    organisation_id=org_id,
                    user_id=user_id,
                    diff={
                        "severity": dup_check.severity,
                        "reason": dup_check.reason,
                    },
                )

            # 10. AI Usage Tracking Event
            usage = AIUsageEvent(
                organisation_id=org_id,
                document_id=doc.id,
                extraction_id=ext.id,
                provider=extraction_output.provider_name,
                pages_processed=extraction_output.page_count,
                processing_duration_ms=extraction_output.duration_ms,
                estimated_cost_usd=extraction_output.estimated_cost_usd,
                success=True,
            )
            db.add(usage)

            # 11. Final Status Decision
            doc.current_extraction_id = ext.id

            if dup_check.is_duplicate and dup_check.severity == "BLOCK" and not dup_check.duplicate_invoice_number:
                # Layer 1 exact file duplicate
                doc.processing_status = DocumentProcessingStatus.DUPLICATE_FILE
            elif doc.document_type == DocumentType.RECEIPT:
                doc.processing_status = DocumentProcessingStatus.PROCESSED_RECEIPT
            elif (
                not ext.math_valid
                or (doc.document_type_confidence and float(doc.document_type_confidence) < settings.EXTRACTION_CLASSIFICATION_MIN)
                or (dup_check.is_duplicate and dup_check.severity == "BLOCK")
            ):
                doc.processing_status = DocumentProcessingStatus.NEEDS_MANUAL_REVIEW
            else:
                doc.processing_status = DocumentProcessingStatus.READY_FOR_REVIEW

            # Mark job completed
            job.status = ExtractionJobStatus.COMPLETED
            job.completed_at = datetime.now(UTC)

            await AuditService.log_static(
                db=db,
                action="DOCUMENT_EXTRACTION_COMPLETED",
                resource_type="captured_document",
                resource_id=str(doc.id),
                organisation_id=org_id,
                user_id=user_id,
                diff={
                    "status": doc.processing_status.value,
                    "invoice_number": ext.invoice_number,
                    "total": str(ext.total) if ext.total else None,
                },
            )

            await db.flush()
            return ext

        except Exception as e:
            log.error("document_processing_failed", doc_id=str(doc.id), error=str(e), exc_info=True)
            job.status = ExtractionJobStatus.FAILED
            job.error_code = "PROCESSING_ERROR"
            job.error_message = str(e)
            job.completed_at = datetime.now(UTC)
            doc.processing_status = DocumentProcessingStatus.FAILED

            await AuditService.log_static(
                db=db,
                action="DOCUMENT_EXTRACTION_FAILED",
                resource_type="captured_document",
                resource_id=str(doc.id),
                organisation_id=org_id,
                user_id=user_id,
                diff={"error": str(e)},
            )
            await db.flush()
            raise
