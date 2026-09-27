"""
Warp Ladger — Document File Security & Validation Service
Validates file headers, authenticates MIME types via magic bytes, enforces size limits,
and computes cryptographic checksums.
"""
import hashlib
import re
from typing import Optional

from app.core.config import settings
from app.core.exceptions import BadRequestError, ValidationFailedError

# Magic byte signatures
MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    "application/pdf": [b"%PDF-"],
    "image/jpeg": [b"\xFF\xD8\xFF"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/webp": [b"RIFF"],
}

HEIC_BRANDS = [b"ftypheic", b"ftypmif1", b"ftypmsf1", b"ftypheix", b"ftyphevc"]


class DocumentSecurityService:
    """Enforces strict pre-processing file validation."""

    @staticmethod
    def inspect_magic_bytes(data: bytes, claimed_content_type: str) -> str:
        """
        Inspects the true binary signature of the file.
        Never trust file extension or browser-provided Content-Type alone.
        """
        if len(data) < 12:
            raise ValidationFailedError("File is empty or too short to be a valid document.")

        # Check PDF
        if data.startswith(b"%PDF-"):
            return "application/pdf"

        # Check JPEG
        if data.startswith(b"\xFF\xD8\xFF"):
            return "image/jpeg"

        # Check PNG
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"

        # Check WebP
        if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return "image/webp"

        # Check HEIC / HEIF
        if len(data) >= 12 and data[4:8] == b"ftyp":
            brand = data[4:12]
            if any(brand.startswith(b) for b in HEIC_BRANDS):
                return "image/heic"

        # If claimed content type is in allowed mimes and file begins with acceptable header in test/mock mode
        if claimed_content_type in settings.DOCUMENT_ALLOWED_MIMES:
            # Allow text/csv or plain test mock formats if claimed appropriately
            if claimed_content_type in ("image/jpeg", "image/png", "application/pdf", "image/heic"):
                raise ValidationFailedError(
                    f"File header does not match claimed MIME type '{claimed_content_type}'."
                )

        raise ValidationFailedError(
            f"Unsupported document format. Allowed formats: PDF, JPEG, PNG, HEIC, WebP."
        )

    @staticmethod
    def validate_file(
        data: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> tuple[str, str, int]:
        """
        Validates size, verifies magic bytes, and returns (verified_mime, sha256_checksum, size_bytes).
        """
        size_bytes = len(data)
        if size_bytes == 0:
            raise ValidationFailedError("Cannot process an empty file.")

        # Inspect binary signature
        verified_mime = DocumentSecurityService.inspect_magic_bytes(data, content_type or "")

        # Check size constraints
        if verified_mime == "application/pdf":
            max_bytes = settings.DOCUMENT_MAX_PDF_SIZE_MB * 1024 * 1024
            if size_bytes > max_bytes:
                raise ValidationFailedError(
                    f"PDF document exceeds maximum allowed size of {settings.DOCUMENT_MAX_PDF_SIZE_MB} MB."
                )
        else:
            max_bytes = settings.DOCUMENT_MAX_IMAGE_SIZE_MB * 1024 * 1024
            if size_bytes > max_bytes:
                raise ValidationFailedError(
                    f"Image document exceeds maximum allowed size of {settings.DOCUMENT_MAX_IMAGE_SIZE_MB} MB."
                )

        # Calculate SHA-256
        sha256 = hashlib.sha256(data).hexdigest()

        return verified_mime, sha256, size_bytes

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Removes path traversal components and dangerous characters."""
        clean = filename.split("/")[-1].split("\\")[-1]
        clean = re.sub(r"[^a-zA-Z0-9._-]", "_", clean)
        return clean or "document.pdf"
