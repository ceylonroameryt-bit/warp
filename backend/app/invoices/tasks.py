"""
Warp Ladger — Invoice ARQ Background Tasks
Handles PDF generation and email sending asynchronously.

Retry behaviour:
- PDF generation: 3 retries with exponential backoff
- Email sending: 3 retries; after all retries → status=FAILED, user notified via audit log
"""
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

log = structlog.get_logger(__name__)

MAX_RETRIES = 3


# ─── Task: Generate PDF ──────────────────────────────────────
async def generate_pdf_task(ctx: dict, invoice_id: str, org_id: str) -> dict:
    """
    ARQ task: generate invoice PDF and store it.
    Called after invoice approval.
    """
    from app.database.base import get_db_session
    from app.invoices.pdf_service import PDFService

    log.info("pdf_task_started", invoice_id=invoice_id)
    try:
        async with get_db_session() as db:
            file_link = await PDFService.generate_and_store(
                db, uuid.UUID(org_id), uuid.UUID(invoice_id)
            )
            await db.commit()
            return {"status": "ok", "file_link_id": str(file_link.id)}
    except Exception as exc:
        log.error("pdf_task_failed", invoice_id=invoice_id, exc=str(exc))
        raise


# ─── Task: Send Email ────────────────────────────────────────
async def send_email_task(ctx: dict, delivery_id: str, message_body: str, attach_pdf: bool = True) -> dict:
    """
    ARQ task: send invoice email via SMTP.
    Updates the InvoiceDelivery record with the outcome.
    Retries up to MAX_RETRIES times on transient failure.
    """
    from sqlalchemy import select
    from app.database.base import get_db_session
    from app.database.models import DeliveryStatus, Invoice, InvoiceDelivery
    from app.invoices.email_service import InvoiceEmailService
    from app.invoices.pdf_service import PDFService

    log.info("email_task_started", delivery_id=delivery_id)

    async with get_db_session() as db:
        result = await db.execute(
            select(InvoiceDelivery).where(InvoiceDelivery.id == uuid.UUID(delivery_id))
        )
        delivery = result.scalar_one_or_none()
        if delivery is None:
            log.warning("email_task_delivery_not_found", delivery_id=delivery_id)
            return {"status": "not_found"}

        delivery.status = DeliveryStatus.PROCESSING
        await db.flush()

        try:
            # Optionally attach PDF
            pdf_bytes = None
            pdf_filename = None
            if attach_pdf:
                try:
                    inv_result = await db.execute(
                        select(Invoice).where(Invoice.id == delivery.invoice_id)
                    )
                    inv = inv_result.scalar_one_or_none()
                    if inv:
                        pdf_url = await PDFService.get_pdf_url(
                            db, delivery.organisation_id, delivery.invoice_id
                        )
                        if not pdf_url:
                            # Generate PDF on-the-fly
                            fl = await PDFService.generate_and_store(
                                db, delivery.organisation_id, delivery.invoice_id
                            )
                            await db.flush()
                        # Read PDF bytes for attachment
                        from pathlib import Path
                        local_path = Path(f"/tmp/ladger_pdfs/{delivery.invoice_id}.pdf")
                        if local_path.exists():
                            pdf_bytes = local_path.read_bytes()
                            pdf_filename = f"{inv.invoice_number}.pdf"
                except Exception as exc:
                    log.warning("email_task_pdf_attach_failed", exc=str(exc))

            await InvoiceEmailService.send_smtp(
                recipient_email=delivery.recipient_email,
                cc=delivery.cc,
                subject=delivery.subject,
                body=message_body,
                pdf_bytes=pdf_bytes,
                pdf_filename=pdf_filename,
            )

            delivery.status = DeliveryStatus.SENT
            delivery.sent_at = datetime.now(UTC)
            await db.commit()
            log.info("email_task_sent", delivery_id=delivery_id)
            return {"status": "sent"}

        except Exception as exc:
            retry = ctx.get("job_try", 1)
            log.warning(
                "email_task_failed",
                delivery_id=delivery_id,
                retry=retry,
                exc=str(exc),
            )
            if retry >= MAX_RETRIES:
                delivery.status = DeliveryStatus.FAILED
                delivery.failure_reason = str(exc)
                delivery.retry_count = retry
            else:
                delivery.status = DeliveryStatus.FAILED_TEMPORARY
                delivery.retry_count = retry
            await db.commit()
            raise  # ARQ will retry automatically


# ─── Helper: enqueue from application code ───────────────────
async def enqueue_send_email(
    delivery_id: str,
    message_body: str,
    attach_pdf: bool = True,
) -> None:
    """Enqueue the send_email_task onto the ARQ Redis queue."""
    import os
    try:
        import arq
        from arq.connections import RedisSettings
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis = await arq.create_pool(RedisSettings.from_dsn(redis_url))
        await redis.enqueue_job(
            "send_email_task",
            delivery_id=delivery_id,
            message_body=message_body,
            attach_pdf=attach_pdf,
        )
        await redis.aclose()
    except Exception as exc:
        log.warning("arq_enqueue_failed", exc=str(exc))
