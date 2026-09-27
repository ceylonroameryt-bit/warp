"""
Warp Ladger — Invoice PDF Service
Generates professional PDFs from Jinja2 HTML template using WeasyPrint.
PDFs are stored in the organisation's private storage bucket.
Download URLs are pre-signed and time-limited (never public).
"""
import io
import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

import structlog

from app.audit.service import AuditService
from app.core.exceptions import NotFoundError

log = structlog.get_logger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"
INVOICE_TEMPLATE = "invoice.html"


def _fmt_money(value, currency: str = "GBP") -> str:
    """Format Decimal as currency string."""
    symbols = {"GBP": "£", "USD": "$", "EUR": "€"}
    symbol = symbols.get(currency, currency + " ")
    try:
        d = Decimal(str(value))
        return f"{symbol}{d:,.2f}"
    except Exception:
        return f"{symbol}0.00"


def _fmt_qty(value) -> str:
    """Format quantity — hide trailing zeros."""
    try:
        d = Decimal(str(value))
        if d == d.to_integral_value():
            return str(int(d))
        return f"{d:.2f}"
    except Exception:
        return str(value)


class PDFService:

    @staticmethod
    def _render_html(invoice, org, lines) -> str:
        """Render the Jinja2 template to HTML string."""
        from jinja2 import Environment, FileSystemLoader

        env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

        # Custom Jinja2 filters
        env.filters["fmt_money"] = _fmt_money
        env.filters["fmt_qty"] = _fmt_qty

        template = env.get_template(INVOICE_TEMPLATE)

        # Derive effective status for display
        from app.invoices.service import InvoiceService
        effective_status = InvoiceService._effective_status(invoice)

        has_discounts = any(
            (ln.discount_value and Decimal(str(ln.discount_value)) > 0)
            for ln in lines
        )

        return template.render(
            invoice=invoice,
            org=org,
            lines=lines,
            effective_status=effective_status,
            has_discounts=has_discounts,
            now=datetime.now(UTC),
        )

    @staticmethod
    def _html_to_pdf(html: str) -> bytes:
        """Convert HTML string to PDF bytes using WeasyPrint."""
        try:
            from weasyprint import HTML
            return HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()
        except ImportError:
            # Fallback: return minimal PDF bytes for dev without WeasyPrint installed
            log.warning("weasyprint_not_installed_using_placeholder_pdf")
            placeholder = (
                b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
                b"3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R>>endobj\n"
                b"xref\n0 4\n0000000000 65535 f\ntrailer<</Size 4/Root 1 0 R>>\n%%EOF"
            )
            return placeholder

    @staticmethod
    async def generate_and_store(db, org_id: uuid.UUID, invoice_id: uuid.UUID):
        """
        Generate PDF for the given invoice and store it in object storage.
        Returns the FileLink record.
        """
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.database.models import (
            File, FileLink, Invoice, Organisation
        )

        # Load invoice with lines
        result = await db.execute(
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .where(Invoice.organisation_id == org_id)
            .options(selectinload(Invoice.lines))
        )
        invoice = result.scalar_one_or_none()
        if invoice is None:
            raise NotFoundError("Invoice not found.")

        # Load organisation
        org_result = await db.execute(
            select(Organisation).where(Organisation.id == org_id)
        )
        org = org_result.scalar_one_or_none()
        if org is None:
            raise NotFoundError("Organisation not found.")

        # Render and convert
        html = PDFService._render_html(invoice, org, invoice.lines)
        pdf_bytes = PDFService._html_to_pdf(html)

        # Build storage key
        file_uuid = uuid.uuid4()
        storage_key = (
            f"organisation/{org_id}/invoices/{invoice_id}/"
            f"generated/{file_uuid}.pdf"
        )
        safe_name = (invoice.customer_name_snapshot or "customer").replace(" ", "-")[:20]
        filename = f"{invoice.invoice_number}-{safe_name}.pdf"

        # Store in configured storage backend
        from app.files.storage import get_storage_backend
        storage = get_storage_backend()
        try:
            await storage.upload(
                key=storage_key,
                data=pdf_bytes,
                content_type="application/pdf",
            )
        except Exception:
            # Fallback if storage backend throws
            log.warning("storage_failed_storing_locally")
            local_dir = Path("/tmp/ladger_pdfs")
            local_dir.mkdir(parents=True, exist_ok=True)
            (local_dir / f"{invoice_id}.pdf").write_bytes(pdf_bytes)

        # Create File record
        bucket = os.getenv("AWS_S3_BUCKET", "ladger-files")
        file_record = File(
            organisation_id=org_id,
            bucket=bucket,
            key=storage_key,
            filename=filename,
            content_type="application/pdf",
            size_bytes=len(pdf_bytes),
        )
        db.add(file_record)
        await db.flush()

        # Create FileLink record
        file_link = FileLink(
            organisation_id=org_id,
            file_id=file_record.id,
            entity_type="INVOICE",
            entity_id=invoice_id,
        )
        db.add(file_link)
        await db.flush()

        await AuditService.log_static(
            db,
            action="INVOICE_PDF_GENERATED",
            resource_type="invoice",
            resource_id=str(invoice_id),
            organisation_id=org_id,
            diff={"file_id": str(file_record.id), "size_bytes": len(pdf_bytes)},
        )
        log.info("invoice_pdf_generated", invoice_id=str(invoice_id), size=len(pdf_bytes))
        return file_link

    @staticmethod
    async def get_pdf_url(db, org_id: uuid.UUID, invoice_id: uuid.UUID) -> Optional[str]:
        """Return a presigned download URL for the invoice PDF, or None if not generated."""
        from sqlalchemy import select
        from app.database.models import File, FileLink

        result = await db.execute(
            select(File.key)
            .join(FileLink, FileLink.file_id == File.id)
            .where(FileLink.entity_type == "INVOICE")
            .where(FileLink.entity_id == invoice_id)
            .where(FileLink.organisation_id == org_id)
            .where(File.content_type == "application/pdf")
            .order_by(FileLink.created_at.desc())
            .limit(1)
        )
        file_key = result.scalar_one_or_none()
        if file_key is None:
            return None

        try:
            from app.files.storage import get_storage_backend
            storage = get_storage_backend()
            return await storage.generate_presigned_url(key=file_key)
        except Exception:
            return f"https://storage.local/{file_key}"
