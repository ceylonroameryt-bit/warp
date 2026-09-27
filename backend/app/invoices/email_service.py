"""
Warp Ladger — Invoice Email Service
Queues invoice delivery records and dispatches ARQ background jobs.
Returns immediately — never holds the HTTP request open for SMTP.

Email security:
- Validates invoice org ownership before queuing
- Rate limits applied at API layer
- Recipient validated as proper email address (Pydantic EmailStr)
- Internal notes never included in customer emails
"""
import uuid
from datetime import UTC, datetime
from typing import Optional

import structlog

from app.core.exceptions import BadRequestError, NotFoundError
from app.database.models import DeliveryStatus, InvoiceDelivery, InvoiceStatus
from app.invoices.schemas import InvoiceSendRequest

log = structlog.get_logger(__name__)

DEFAULT_SUBJECT_TEMPLATE = "Invoice {invoice_number} from {org_name}"
DEFAULT_MESSAGE_TEMPLATE = """Hi {customer_name},

Please find attached invoice {invoice_number} for {total}.

Payment is due by {due_date}.

If you have any questions, please don't hesitate to get in touch.

Thank you for your business.

{org_name}"""


class InvoiceEmailService:

    @staticmethod
    def _build_subject(invoice, org) -> str:
        return DEFAULT_SUBJECT_TEMPLATE.format(
            invoice_number=invoice.invoice_number or "Draft",
            org_name=org.name,
        )

    @staticmethod
    def _build_message(invoice, org) -> str:
        from decimal import Decimal
        total_str = f"{invoice.currency} {Decimal(str(invoice.total)):,.2f}"
        due_date_str = invoice.due_date.strftime("%d %B %Y") if invoice.due_date else "N/A"
        return DEFAULT_MESSAGE_TEMPLATE.format(
            customer_name=invoice.customer_name_snapshot or "Valued Customer",
            invoice_number=invoice.invoice_number or "Draft",
            total=total_str,
            due_date=due_date_str,
            org_name=org.name,
        )

    @staticmethod
    async def queue_send(
        db,
        org_id: uuid.UUID,
        invoice_id: uuid.UUID,
        send_request: InvoiceSendRequest,
        user_id: uuid.UUID,
    ) -> InvoiceDelivery:
        """
        1. Validate invoice is sendable
        2. Create a QUEUED InvoiceDelivery record
        3. Update invoice status (APPROVED → SENT)
        4. Dispatch ARQ job
        5. Return delivery record immediately
        """
        from sqlalchemy import select
        from app.database.models import Invoice, Organisation

        # Load and validate
        result = await db.execute(
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .where(Invoice.organisation_id == org_id)
        )
        invoice = result.scalar_one_or_none()
        if invoice is None:
            raise NotFoundError("Invoice not found.")

        if invoice.status == InvoiceStatus.DRAFT:
            raise BadRequestError(
                "Approve the invoice before sending.", code="INVALID_INVOICE_STATUS"
            )
        if invoice.status == InvoiceStatus.VOID:
            raise BadRequestError("Cannot send a voided invoice.", code="INVALID_INVOICE_STATUS")

        # Load org for template rendering
        org_result = await db.execute(
            select(Organisation).where(Organisation.id == org_id)
        )
        org = org_result.scalar_one_or_none()

        subject = send_request.subject or InvoiceEmailService._build_subject(invoice, org)

        # Create delivery record
        delivery = InvoiceDelivery(
            organisation_id=org_id,
            invoice_id=invoice_id,
            recipient_email=send_request.recipient_email,
            cc=send_request.cc,
            subject=subject,
            status=DeliveryStatus.QUEUED,
            sent_by_id=user_id,
        )
        db.add(delivery)

        # Transition invoice to SENT if it was APPROVED
        if invoice.status == InvoiceStatus.APPROVED:
            invoice.status = InvoiceStatus.SENT
            invoice.sent_at = datetime.now(UTC)

        await db.flush()

        # Dispatch ARQ job (fire-and-forget)
        try:
            from app.invoices.tasks import enqueue_send_email
            await enqueue_send_email(
                delivery_id=str(delivery.id),
                message_body=send_request.message or InvoiceEmailService._build_message(invoice, org),
                attach_pdf=send_request.attach_pdf,
            )
        except Exception as exc:
            # Non-fatal: job will retry or can be manually retried
            log.warning("email_job_enqueue_failed", exc=str(exc), delivery_id=str(delivery.id))

        log.info(
            "invoice_email_queued",
            invoice_id=str(invoice_id),
            recipient=send_request.recipient_email,
            delivery_id=str(delivery.id),
        )
        return delivery

    @staticmethod
    async def send_smtp(
        recipient_email: str,
        cc: Optional[str],
        subject: str,
        body: str,
        pdf_bytes: Optional[bytes] = None,
        pdf_filename: Optional[str] = None,
    ) -> None:
        """
        Send email via SMTP using aiosmtplib.
        Called from the ARQ worker — never from an HTTP handler directly.
        """
        import os
        import aiosmtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders

        smtp_host = os.getenv("SMTP_HOST", "localhost")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USERNAME", "")
        smtp_pass = os.getenv("SMTP_PASSWORD", "")
        smtp_from = os.getenv("SMTP_FROM_EMAIL", "noreply@ladger.app")
        smtp_tls = os.getenv("SMTP_STARTTLS", "true").lower() == "true"

        msg = MIMEMultipart()
        msg["From"] = smtp_from
        msg["To"] = recipient_email
        if cc:
            msg["Cc"] = cc
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        if pdf_bytes and pdf_filename:
            attachment = MIMEBase("application", "pdf")
            attachment.set_payload(pdf_bytes)
            encoders.encode_base64(attachment)
            attachment.add_header(
                "Content-Disposition",
                f'attachment; filename="{pdf_filename}"',
            )
            msg.attach(attachment)

        await aiosmtplib.send(
            msg,
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user or None,
            password=smtp_pass or None,
            start_tls=smtp_tls,
        )
        log.info("invoice_email_sent_smtp", recipient=recipient_email)
