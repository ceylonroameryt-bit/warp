"""
Warp Ladger — Multi-Tenant Supplier Matching Service
Matches extracted invoice data against existing Phase 2 suppliers.
Never searches across organisation boundaries.
"""
import difflib
import re
import uuid
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Contact, ContactType
from app.documents.schemas import SupplierMatchResponse

log = structlog.get_logger(__name__)

# Common company suffixes to strip when normalizing business names
SUFFIX_PATTERN = re.compile(
    r"\b(limited|ltd|plc|llc|inc|incorporated|corp|corporation|gmbh|co|company)\b",
    re.IGNORECASE,
)

GENERIC_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "icloud.com",
    "aol.com",
}


def normalize_name(name: Optional[str]) -> str:
    """Normalizes a company name for fuzzy matching."""
    if not name:
        return ""
    # Lowercase & remove punctuation
    clean = re.sub(r"[^\w\s]", " ", name.lower())
    # Remove company suffixes
    clean = SUFFIX_PATTERN.sub("", clean)
    # Collapse whitespace
    return " ".join(clean.split())


def normalize_tax_number(vat: Optional[str]) -> str:
    """Strips spaces, hyphens, and standardizes uppercase."""
    if not vat:
        return ""
    return re.sub(r"[^A-Z0-9]", "", vat.upper())


class SupplierMatchingService:
    """Matches extracted documents to existing Contacts in the same organisation."""

    @staticmethod
    async def match_supplier(
        db: AsyncSession,
        org_id: uuid.UUID,
        extracted_name: Optional[str],
        extracted_vat: Optional[str] = None,
        extracted_company_number: Optional[str] = None,
        extracted_email: Optional[str] = None,
    ) -> SupplierMatchResponse:
        """
        Executes multi-layered supplier matching in priority order:
        1. VAT number exact match (highest confidence)
        2. Company registration number exact match
        3. Email domain match
        4. Normalized business name similarity
        """
        # Fetch all active suppliers in this tenant
        result = await db.execute(
            select(Contact)
            .where(Contact.organisation_id == org_id)
            .where(Contact.deleted_at.is_(None))
            .where(Contact.contact_type.in_([ContactType.SUPPLIER, ContactType.BOTH]))
        )
        suppliers = result.scalars().all()

        if not suppliers:
            return SupplierMatchResponse(
                is_exact_match=False,
                match_reason="No existing suppliers found in organisation",
            )

        # ── 1. VAT Number Exact Match ─────────────────────────
        norm_vat = normalize_tax_number(extracted_vat)
        if norm_vat:
            for s in suppliers:
                s_vat = normalize_tax_number(s.vat_number)
                if s_vat and s_vat == norm_vat:
                    return SupplierMatchResponse(
                        matched_supplier_id=s.id,
                        supplier_name=s.business_name,
                        vat_number=s.vat_number,
                        email=s.email,
                        confidence=Decimal("1.00"),
                        match_reason="Exact VAT number match",
                        is_exact_match=True,
                    )

        # ── 2. Company Registration Number Exact Match ────────
        norm_comp = normalize_tax_number(extracted_company_number)
        if norm_comp:
            for s in suppliers:
                s_comp = normalize_tax_number(s.company_number)
                if s_comp and s_comp == norm_comp:
                    return SupplierMatchResponse(
                        matched_supplier_id=s.id,
                        supplier_name=s.business_name,
                        vat_number=s.vat_number,
                        email=s.email,
                        confidence=Decimal("0.98"),
                        match_reason="Exact company registration number match",
                        is_exact_match=True,
                    )

        # ── 3. Email Domain Match ─────────────────────────────
        if extracted_email and "@" in extracted_email:
            ext_domain = extracted_email.split("@")[-1].lower().strip()
            if ext_domain not in GENERIC_EMAIL_DOMAINS:
                for s in suppliers:
                    if s.email and "@" in s.email:
                        s_domain = s.email.split("@")[-1].lower().strip()
                        if s_domain == ext_domain:
                            return SupplierMatchResponse(
                                matched_supplier_id=s.id,
                                supplier_name=s.business_name,
                                vat_number=s.vat_number,
                                email=s.email,
                                confidence=Decimal("0.90"),
                                match_reason=f"Email domain match (@{ext_domain})",
                                is_exact_match=False,
                            )

        # ── 4. Normalized Business Name Similarity ────────────
        norm_ext_name = normalize_name(extracted_name)
        if norm_ext_name:
            best_match: Optional[Contact] = None
            best_score = 0.0

            for s in suppliers:
                norm_s_name = normalize_name(s.business_name)
                if not norm_s_name:
                    continue

                if norm_s_name == norm_ext_name:
                    return SupplierMatchResponse(
                        matched_supplier_id=s.id,
                        supplier_name=s.business_name,
                        vat_number=s.vat_number,
                        email=s.email,
                        confidence=Decimal("0.96"),
                        match_reason="Exact business name match (normalized)",
                        is_exact_match=True,
                    )

                # Substring containment check
                if norm_s_name in norm_ext_name or norm_ext_name in norm_s_name:
                    score = 0.88
                else:
                    # Sequence matcher ratio
                    score = difflib.SequenceMatcher(None, norm_ext_name, norm_s_name).ratio()

                if score > best_score:
                    best_score = score
                    best_match = s

            # Threshold for fuzzy name match
            if best_match and best_score >= 0.80:
                conf = Decimal(str(round(best_score, 2)))
                return SupplierMatchResponse(
                    matched_supplier_id=best_match.id,
                    supplier_name=best_match.business_name,
                    vat_number=best_match.vat_number,
                    email=best_match.email,
                    confidence=conf,
                    match_reason=f"Fuzzy name match ({int(best_score * 100)}% similarity)",
                    is_exact_match=False,
                )

        return SupplierMatchResponse(
            is_exact_match=False,
            match_reason="No matching supplier detected",
        )
