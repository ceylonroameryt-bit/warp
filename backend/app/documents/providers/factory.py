"""
Warp Ladger — Document Extraction Provider Factory
"""
from functools import lru_cache
from app.core.config import settings
from app.documents.providers.base import DocumentExtractionProvider
from app.documents.providers.fake_provider import FakeDocumentProvider
from app.documents.providers.google_docai import GoogleDocumentAIProvider


@lru_cache
def get_document_provider() -> DocumentExtractionProvider:
    """Returns the configured extraction provider."""
    provider_name = settings.DOCUMENT_PROVIDER.lower()
    if provider_name == "google_document_ai":
        return GoogleDocumentAIProvider()
    return FakeDocumentProvider()
