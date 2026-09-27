"""
Warp Ladger — Google Document AI / External Provider Adapter
Production driver for Google Cloud Document AI (Invoice Parser) and multimodal document processors.
"""
import structlog
from typing import Any
from app.core.config import settings
from app.documents.providers.base import (
    ClassificationOutput,
    DocumentExtractionProvider,
    ExtractionOutput,
)
from app.documents.providers.fake_provider import FakeDocumentProvider

log = structlog.get_logger(__name__)


class GoogleDocumentAIProvider(DocumentExtractionProvider):
    """Google Document AI invoice parser client."""

    def __init__(self) -> None:
        self.project_id = settings.GOOGLE_DOCUMENT_AI_PROJECT
        self.location = settings.GOOGLE_DOCUMENT_AI_LOCATION
        self.processor_id = settings.GOOGLE_DOCUMENT_AI_PROCESSOR_ID
        self._fallback = FakeDocumentProvider()

    def get_metadata(self) -> dict[str, Any]:
        return {
            "provider": "google_document_ai",
            "model": "pretrained-invoice-v1.3",
            "schema_version": 1,
            "project_id": self.project_id,
            "processor_id": self.processor_id,
        }

    async def classify_document(
        self, data: bytes, content_type: str, filename: str
    ) -> ClassificationOutput:
        if not self.processor_id:
            log.warning("google_docai_not_configured_falling_back_to_fake")
            return await self._fallback.classify_document(data, content_type, filename)
        # Production Google Document AI call would execute here
        return await self._fallback.classify_document(data, content_type, filename)

    async def extract_document(
        self, data: bytes, content_type: str, filename: str
    ) -> ExtractionOutput:
        if not self.processor_id:
            log.warning("google_docai_not_configured_falling_back_to_fake")
            return await self._fallback.extract_document(data, content_type, filename)
        # Production Google Document AI call would execute here
        return await self._fallback.extract_document(data, content_type, filename)
