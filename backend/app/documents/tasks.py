"""
Warp Ladger — Document Background Processing Tasks (ARQ / Async Worker)
"""
import uuid
from typing import Any, Optional

import structlog

from app.database.base import AsyncSessionLocal
from app.documents.services.processing_service import DocumentProcessingService

log = structlog.get_logger(__name__)


async def process_document_task(
    ctx: dict[str, Any],
    org_id_str: str,
    document_id_str: str,
    user_id_str: Optional[str] = None,
) -> dict[str, Any]:
    """
    ARQ worker task to process a captured document asynchronously.
    """
    org_id = uuid.UUID(org_id_str)
    doc_id = uuid.UUID(document_id_str)
    user_id = uuid.UUID(user_id_str) if user_id_str else None

    log.info("starting_background_document_task", org_id=org_id_str, document_id=document_id_str)

    async with AsyncSessionLocal() as db:
        async with db.begin():
            ext = await DocumentProcessingService.process_document(
                db=db,
                org_id=org_id,
                document_id=doc_id,
                user_id=user_id,
            )
            return {
                "status": "success",
                "document_id": str(doc_id),
                "extraction_id": str(ext.id),
                "invoice_number": ext.invoice_number,
                "total": str(ext.total) if ext.total else None,
            }
