"""
Warp Ladger — Contacts Service
Full business contact management layer with strict multi-tenant isolation,
duplicate detection, sub-resource lifecycle, and CSV import/export.
"""
import csv
import io
import re
import uuid
from datetime import UTC, datetime
from typing import Any, Optional

import structlog
from sqlalchemy import desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.contacts.schemas import (
    ContactAddressCreate,
    ContactAddressUpdate,
    ContactCreate,
    ContactDocumentResponse,
    ContactImportPreviewResult,
    ContactImportRowValidation,
    ContactNoteResponse,
    ContactPersonCreate,
    ContactPersonUpdate,
    ContactQuickCreate,
    ContactResponse,
    ContactUpdate,
    DuplicateCheckResponse,
    DuplicateMatch,
)
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.database.models import (
    AddressType,
    Contact,
    ContactAddress,
    ContactNote,
    ContactPerson,
    ContactStatus,
    ContactType,
    File,
    FileLink,
    PaymentTerm,
    User,
)

log = structlog.get_logger(__name__)


# ─── Normalization Utilities ─────────────────────────────────
def normalize_string(val: Optional[str]) -> str:
    if not val:
        return ""
    return re.sub(r"\s+", " ", val.strip().lower())


def normalize_code(val: Optional[str]) -> str:
    if not val:
        return ""
    return re.sub(r"[^A-Za-z0-9]", "", val).upper()


def normalize_business_name(name: str) -> str:
    cleaned = normalize_string(name)
    # Strip common legal suffixes for fuzzy matching
    suffixes = [
        " limited", " ltd", " plc", " llc", " inc", " corp", " corporation",
        " gmbh", " sarl", " bv", " pty", " co", " company"
    ]
    for s in suffixes:
        if cleaned.endswith(s):
            cleaned = cleaned[: -len(s)].strip()
            break
    return cleaned


class ContactService:

    # ─── Duplicate Detection ──────────────────────────────────
    @staticmethod
    async def check_duplicates(
        db: AsyncSession,
        org_id: uuid.UUID,
        business_name: str,
        email: Optional[str] = None,
        vat_number: Optional[str] = None,
        company_number: Optional[str] = None,
        exclude_contact_id: Optional[uuid.UUID] = None,
    ) -> DuplicateCheckResponse:
        norm_name = normalize_business_name(business_name)
        norm_email = normalize_string(email) if email else None
        norm_vat = normalize_code(vat_number) if vat_number else None
        norm_comp = normalize_code(company_number) if company_number else None

        # Fetch existing active contacts in this org
        query = (
            select(Contact)
            .where(Contact.organisation_id == org_id)
            .where(Contact.deleted_at.is_(None))
        )
        if exclude_contact_id:
            query = query.where(Contact.id != exclude_contact_id)

        result = await db.execute(query)
        existing_contacts = result.scalars().all()

        matches: list[DuplicateMatch] = []

        for c in existing_contacts:
            matched_fields = []
            confidence = "LOW"
            messages = []

            # 1. Exact VAT Match (High confidence)
            if norm_vat and c.vat_number:
                if normalize_code(c.vat_number) == norm_vat:
                    matched_fields.append("vat_number")
                    confidence = "HIGH"
                    messages.append(f"Identical VAT Number ({c.vat_number})")

            # 2. Exact Company Number Match (High confidence)
            if norm_comp and c.company_number:
                if normalize_code(c.company_number) == norm_comp:
                    matched_fields.append("company_number")
                    confidence = "HIGH"
                    messages.append(f"Identical Company Number ({c.company_number})")

            # 3. Normalized Email Match (Medium confidence)
            if norm_email and c.email:
                if normalize_string(c.email) == norm_email:
                    matched_fields.append("email")
                    if confidence != "HIGH":
                        confidence = "MEDIUM"
                    messages.append(f"Matching email address ({c.email})")

            # 4. Normalized Business Name Match
            c_norm_name = normalize_business_name(c.business_name)
            if norm_name and c_norm_name:
                if norm_name == c_norm_name:
                    matched_fields.append("business_name")
                    if confidence != "HIGH":
                        confidence = "MEDIUM"
                    messages.append("Identical or near-identical business name")

            if matched_fields:
                matches.append(
                    DuplicateMatch(
                        contact_id=c.id,
                        business_name=c.business_name,
                        matched_fields=matched_fields,
                        confidence=confidence,
                        message="; ".join(messages),
                    )
                )

        return DuplicateCheckResponse(
            has_duplicates=len(matches) > 0,
            matches=matches,
        )

    # ─── Contact CRUD ─────────────────────────────────────────
    @staticmethod
    async def create_contact(
        db: AsyncSession,
        org_id: uuid.UUID,
        data: ContactCreate,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> Contact:
        # Cross-tenant check for payment terms
        if data.payment_terms_id:
            pt_res = await db.execute(
                select(PaymentTerm)
                .where(PaymentTerm.id == data.payment_terms_id)
                .where(PaymentTerm.organisation_id == org_id)
            )
            if pt_res.scalar_one_or_none() is None:
                raise BadRequestError("Referenced payment term does not exist in this organisation.")

        contact = Contact(
            organisation_id=org_id,
            contact_type=data.contact_type,
            status=data.status,
            business_name=data.business_name.strip(),
            legal_name=data.legal_name.strip() if data.legal_name else None,
            display_name=data.display_name.strip() if data.display_name else None,
            first_name=data.first_name.strip() if data.first_name else None,
            last_name=data.last_name.strip() if data.last_name else None,
            email=data.email.strip().lower() if data.email else None,
            phone=data.phone.strip() if data.phone else None,
            mobile=data.mobile.strip() if data.mobile else None,
            website=data.website.strip() if data.website else None,
            company_number=data.company_number.strip().upper() if data.company_number else None,
            vat_number=data.vat_number.strip().upper() if data.vat_number else None,
            tax_identifier=data.tax_identifier.strip() if data.tax_identifier else None,
            currency=data.currency.strip().upper(),
            payment_terms_id=data.payment_terms_id,
            reference=data.reference.strip() if data.reference else None,
            credit_limit=data.credit_limit,
            notes=data.notes,
            created_by_id=current_user_id,
        )
        db.add(contact)
        await db.flush()

        # Add primary contact person if provided
        if data.primary_contact:
            person = ContactPerson(
                organisation_id=org_id,
                contact_id=contact.id,
                first_name=data.primary_contact.first_name.strip(),
                last_name=data.primary_contact.last_name.strip() if data.primary_contact.last_name else None,
                job_title=data.primary_contact.job_title.strip() if data.primary_contact.job_title else None,
                email=data.primary_contact.email.strip().lower() if data.primary_contact.email else None,
                phone=data.primary_contact.phone.strip() if data.primary_contact.phone else None,
                mobile=data.primary_contact.mobile.strip() if data.primary_contact.mobile else None,
                department=data.primary_contact.department.strip() if data.primary_contact.department else None,
                is_primary=True,
                status=data.primary_contact.status,
            )
            db.add(person)

        # Add billing address if provided
        if data.billing_address:
            billing = ContactAddress(
                organisation_id=org_id,
                contact_id=contact.id,
                address_type=AddressType.BILLING,
                line1=data.billing_address.line1.strip(),
                line2=data.billing_address.line2.strip() if data.billing_address.line2 else None,
                city=data.billing_address.city.strip(),
                county_region=data.billing_address.county_region.strip() if data.billing_address.county_region else None,
                postcode=data.billing_address.postcode.strip().upper() if data.billing_address.postcode else None,
                country_code=data.billing_address.country_code.strip().upper(),
                is_primary=True,
            )
            db.add(billing)

        # Add shipping address if provided
        if data.shipping_address:
            shipping = ContactAddress(
                organisation_id=org_id,
                contact_id=contact.id,
                address_type=AddressType.SHIPPING,
                line1=data.shipping_address.line1.strip(),
                line2=data.shipping_address.line2.strip() if data.shipping_address.line2 else None,
                city=data.shipping_address.city.strip(),
                county_region=data.shipping_address.county_region.strip() if data.shipping_address.county_region else None,
                postcode=data.shipping_address.postcode.strip().upper() if data.shipping_address.postcode else None,
                country_code=data.shipping_address.country_code.strip().upper(),
                is_primary=True,
            )
            db.add(shipping)

        await db.flush()
        log.info("contact_created", org_id=str(org_id), contact_id=str(contact.id), name=contact.business_name)
        return contact

    @staticmethod
    async def quick_create(
        db: AsyncSession,
        org_id: uuid.UUID,
        data: ContactQuickCreate,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> Contact:
        contact = Contact(
            organisation_id=org_id,
            contact_type=data.contact_type,
            business_name=data.business_name.strip(),
            email=data.email.strip().lower() if data.email else None,
            phone=data.phone.strip() if data.phone else None,
            currency=data.currency.strip().upper(),
            status=ContactStatus.ACTIVE,
            created_by_id=current_user_id,
        )
        db.add(contact)
        await db.flush()
        log.info("contact_quick_created", org_id=str(org_id), contact_id=str(contact.id), name=contact.business_name)
        return contact

    @staticmethod
    async def get_contact(
        db: AsyncSession,
        org_id: uuid.UUID,
        contact_id: uuid.UUID,
        load_details: bool = False,
    ) -> Contact:
        query = (
            select(Contact)
            .where(Contact.id == contact_id)
            .where(Contact.organisation_id == org_id)
            .where(Contact.deleted_at.is_(None))
        )
        if load_details:
            query = query.options(
                selectinload(Contact.people),
                selectinload(Contact.addresses),
                selectinload(Contact.internal_notes).selectinload(ContactNote.created_by),
                selectinload(Contact.payment_terms),
                selectinload(Contact.tags),
            )
        else:
            query = query.options(
                selectinload(Contact.people),
                selectinload(Contact.payment_terms),
            )

        result = await db.execute(query)
        contact = result.scalar_one_or_none()
        if not contact:
            raise NotFoundError("Contact not found in this organisation.")
        return contact

    @staticmethod
    async def update_contact(
        db: AsyncSession,
        org_id: uuid.UUID,
        contact_id: uuid.UUID,
        data: ContactUpdate,
    ) -> tuple[Contact, dict[str, Any]]:
        contact = await ContactService.get_contact(db, org_id, contact_id, load_details=True)
        diff: dict[str, Any] = {}

        # Cross-tenant check for payment terms if updated
        if data.payment_terms_id is not None and data.payment_terms_id != contact.payment_terms_id:
            pt_res = await db.execute(
                select(PaymentTerm)
                .where(PaymentTerm.id == data.payment_terms_id)
                .where(PaymentTerm.organisation_id == org_id)
            )
            if pt_res.scalar_one_or_none() is None:
                raise BadRequestError("Referenced payment term does not exist in this organisation.")
            diff["payment_terms_id"] = {
                "before": str(contact.payment_terms_id) if contact.payment_terms_id else None,
                "after": str(data.payment_terms_id),
            }
            contact.payment_terms_id = data.payment_terms_id

        # Update scalar fields and compute diff
        fields = [
            ("contact_type", data.contact_type),
            ("business_name", data.business_name.strip() if data.business_name else None),
            ("legal_name", data.legal_name.strip() if data.legal_name else None),
            ("display_name", data.display_name.strip() if data.display_name else None),
            ("first_name", data.first_name.strip() if data.first_name else None),
            ("last_name", data.last_name.strip() if data.last_name else None),
            ("email", data.email.strip().lower() if data.email else None),
            ("phone", data.phone.strip() if data.phone else None),
            ("mobile", data.mobile.strip() if data.mobile else None),
            ("website", data.website.strip() if data.website else None),
            ("company_number", data.company_number.strip().upper() if data.company_number else None),
            ("vat_number", data.vat_number.strip().upper() if data.vat_number else None),
            ("tax_identifier", data.tax_identifier.strip() if data.tax_identifier else None),
            ("currency", data.currency.strip().upper() if data.currency else None),
            ("reference", data.reference.strip() if data.reference else None),
            ("credit_limit", data.credit_limit),
            ("notes", data.notes),
            ("status", data.status),
        ]

        for field_name, new_val in fields:
            if new_val is not None:
                old_val = getattr(contact, field_name)
                if old_val != new_val:
                    diff[field_name] = {
                        "before": old_val.value if hasattr(old_val, "value") else old_val,
                        "after": new_val.value if hasattr(new_val, "value") else new_val,
                    }
                    setattr(contact, field_name, new_val)

        await db.flush()
        return contact, diff

    @staticmethod
    async def archive_contact(db: AsyncSession, org_id: uuid.UUID, contact_id: uuid.UUID) -> Contact:
        contact = await ContactService.get_contact(db, org_id, contact_id)
        contact.status = ContactStatus.ARCHIVED
        contact.archived_at = datetime.now(UTC)
        await db.flush()
        log.info("contact_archived", org_id=str(org_id), contact_id=str(contact_id))
        return contact

    @staticmethod
    async def restore_contact(db: AsyncSession, org_id: uuid.UUID, contact_id: uuid.UUID) -> Contact:
        contact = await ContactService.get_contact(db, org_id, contact_id)
        contact.status = ContactStatus.ACTIVE
        contact.archived_at = None
        await db.flush()
        log.info("contact_restored", org_id=str(org_id), contact_id=str(contact_id))
        return contact

    @staticmethod
    async def list_contacts(
        db: AsyncSession,
        org_id: uuid.UUID,
        contact_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        country_code: Optional[str] = None,
        currency: Optional[str] = None,
        payment_terms_id: Optional[uuid.UUID] = None,
        sort_by: str = "name_asc",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Contact], int]:
        # Bound page and page_size
        page = max(1, page)
        page_size = min(100, max(1, page_size))

        query = (
            select(Contact)
            .where(Contact.organisation_id == org_id)
            .where(Contact.deleted_at.is_(None))
            .options(
                selectinload(Contact.people),
                selectinload(Contact.payment_terms),
            )
        )

        # Status filter
        if status:
            if status.upper() != "ALL":
                try:
                    c_status = ContactStatus(status.upper())
                    query = query.where(Contact.status == c_status)
                except ValueError:
                    pass
        else:
            # Default: show ACTIVE and INACTIVE, exclude ARCHIVED
            query = query.where(Contact.status != ContactStatus.ARCHIVED)

        # Contact Type filter
        if contact_type:
            ct_upper = contact_type.upper()
            if ct_upper == "CUSTOMER":
                query = query.where(Contact.contact_type.in_([ContactType.CUSTOMER, ContactType.BOTH]))
            elif ct_upper == "SUPPLIER":
                query = query.where(Contact.contact_type.in_([ContactType.SUPPLIER, ContactType.BOTH]))
            elif ct_upper == "BOTH":
                query = query.where(Contact.contact_type == ContactType.BOTH)

        # Currency filter
        if currency:
            query = query.where(Contact.currency == currency.upper())

        # Payment terms filter
        if payment_terms_id:
            query = query.where(Contact.payment_terms_id == payment_terms_id)

        # Search filter across multiple fields
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Contact.business_name.ilike(term),
                    Contact.legal_name.ilike(term),
                    Contact.display_name.ilike(term),
                    Contact.email.ilike(term),
                    Contact.phone.ilike(term),
                    Contact.mobile.ilike(term),
                    Contact.company_number.ilike(term),
                    Contact.vat_number.ilike(term),
                    Contact.reference.ilike(term),
                )
            )

        # Country filter via addresses join
        if country_code and country_code.strip():
            c_code = country_code.strip().upper()
            query = query.join(Contact.addresses).where(ContactAddress.country_code == c_code).distinct()

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # Sorting
        if sort_by == "name_desc":
            query = query.order_by(Contact.business_name.desc())
        elif sort_by == "created_desc":
            query = query.order_by(Contact.created_at.desc())
        elif sort_by == "updated_desc":
            query = query.order_by(Contact.updated_at.desc())
        else:  # name_asc
            query = query.order_by(Contact.business_name.asc())

        # Pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        items = list(result.scalars().all())

        return items, total

    # ─── Contact People ───────────────────────────────────────
    @staticmethod
    async def add_person(
        db: AsyncSession,
        org_id: uuid.UUID,
        contact_id: uuid.UUID,
        data: ContactPersonCreate,
    ) -> ContactPerson:
        # Verify contact exists in this org
        await ContactService.get_contact(db, org_id, contact_id)

        if data.is_primary:
            await db.execute(
                update(ContactPerson)
                .where(ContactPerson.contact_id == contact_id)
                .where(ContactPerson.organisation_id == org_id)
                .values(is_primary=False)
            )

        person = ContactPerson(
            organisation_id=org_id,
            contact_id=contact_id,
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip() if data.last_name else None,
            job_title=data.job_title.strip() if data.job_title else None,
            email=data.email.strip().lower() if data.email else None,
            phone=data.phone.strip() if data.phone else None,
            mobile=data.mobile.strip() if data.mobile else None,
            department=data.department.strip() if data.department else None,
            is_primary=data.is_primary,
            status=data.status,
        )
        db.add(person)
        await db.flush()
        return person

    @staticmethod
    async def update_person(
        db: AsyncSession,
        org_id: uuid.UUID,
        contact_id: uuid.UUID,
        person_id: uuid.UUID,
        data: ContactPersonUpdate,
    ) -> tuple[ContactPerson, dict[str, Any]]:
        result = await db.execute(
            select(ContactPerson)
            .where(ContactPerson.id == person_id)
            .where(ContactPerson.contact_id == contact_id)
            .where(ContactPerson.organisation_id == org_id)
        )
        person = result.scalar_one_or_none()
        if not person:
            raise NotFoundError("Contact person not found in this contact.")

        diff: dict[str, Any] = {}
        if data.is_primary is True and not person.is_primary:
            await db.execute(
                update(ContactPerson)
                .where(ContactPerson.contact_id == contact_id)
                .where(ContactPerson.organisation_id == org_id)
                .values(is_primary=False)
            )
            diff["is_primary"] = {"before": False, "after": True}
            person.is_primary = True
        elif data.is_primary is False and person.is_primary:
            diff["is_primary"] = {"before": True, "after": False}
            person.is_primary = False

        fields = [
            ("first_name", data.first_name.strip() if data.first_name else None),
            ("last_name", data.last_name.strip() if data.last_name else None),
            ("job_title", data.job_title.strip() if data.job_title else None),
            ("email", data.email.strip().lower() if data.email else None),
            ("phone", data.phone.strip() if data.phone else None),
            ("mobile", data.mobile.strip() if data.mobile else None),
            ("department", data.department.strip() if data.department else None),
            ("status", data.status),
        ]
        for field_name, new_val in fields:
            if new_val is not None:
                old_val = getattr(person, field_name)
                if old_val != new_val:
                    diff[field_name] = {"before": old_val, "after": new_val}
                    setattr(person, field_name, new_val)

        await db.flush()
        return person, diff

    @staticmethod
    async def delete_person(
        db: AsyncSession,
        org_id: uuid.UUID,
        contact_id: uuid.UUID,
        person_id: uuid.UUID,
    ) -> None:
        result = await db.execute(
            select(ContactPerson)
            .where(ContactPerson.id == person_id)
            .where(ContactPerson.contact_id == contact_id)
            .where(ContactPerson.organisation_id == org_id)
        )
        person = result.scalar_one_or_none()
        if not person:
            raise NotFoundError("Contact person not found in this contact.")
        await db.delete(person)
        await db.flush()

    # ─── Contact Addresses ───────────────────────────────────
    @staticmethod
    async def add_address(
        db: AsyncSession,
        org_id: uuid.UUID,
        contact_id: uuid.UUID,
        data: ContactAddressCreate,
    ) -> ContactAddress:
        await ContactService.get_contact(db, org_id, contact_id)

        if data.is_primary:
            await db.execute(
                update(ContactAddress)
                .where(ContactAddress.contact_id == contact_id)
                .where(ContactAddress.organisation_id == org_id)
                .where(ContactAddress.address_type == data.address_type)
                .values(is_primary=False)
            )

        address = ContactAddress(
            organisation_id=org_id,
            contact_id=contact_id,
            address_type=data.address_type,
            line1=data.line1.strip(),
            line2=data.line2.strip() if data.line2 else None,
            city=data.city.strip(),
            county_region=data.county_region.strip() if data.county_region else None,
            postcode=data.postcode.strip().upper() if data.postcode else None,
            country_code=data.country_code.strip().upper(),
            is_primary=data.is_primary,
        )
        db.add(address)
        await db.flush()
        return address

    @staticmethod
    async def update_address(
        db: AsyncSession,
        org_id: uuid.UUID,
        contact_id: uuid.UUID,
        address_id: uuid.UUID,
        data: ContactAddressUpdate,
    ) -> tuple[ContactAddress, dict[str, Any]]:
        result = await db.execute(
            select(ContactAddress)
            .where(ContactAddress.id == address_id)
            .where(ContactAddress.contact_id == contact_id)
            .where(ContactAddress.organisation_id == org_id)
        )
        address = result.scalar_one_or_none()
        if not address:
            raise NotFoundError("Address not found for this contact.")

        diff: dict[str, Any] = {}
        if data.is_primary is True and not address.is_primary:
            addr_type = data.address_type or address.address_type
            await db.execute(
                update(ContactAddress)
                .where(ContactAddress.contact_id == contact_id)
                .where(ContactAddress.organisation_id == org_id)
                .where(ContactAddress.address_type == addr_type)
                .values(is_primary=False)
            )
            diff["is_primary"] = {"before": False, "after": True}
            address.is_primary = True
        elif data.is_primary is False and address.is_primary:
            diff["is_primary"] = {"before": True, "after": False}
            address.is_primary = False

        if data.address_type is not None and data.address_type != address.address_type:
            diff["address_type"] = {"before": address.address_type.value, "after": data.address_type.value}
            address.address_type = data.address_type

        fields = [
            ("line1", data.line1.strip() if data.line1 else None),
            ("line2", data.line2.strip() if data.line2 else None),
            ("city", data.city.strip() if data.city else None),
            ("county_region", data.county_region.strip() if data.county_region else None),
            ("postcode", data.postcode.strip().upper() if data.postcode else None),
            ("country_code", data.country_code.strip().upper() if data.country_code else None),
        ]
        for field_name, new_val in fields:
            if new_val is not None:
                old_val = getattr(address, field_name)
                if old_val != new_val:
                    diff[field_name] = {"before": old_val, "after": new_val}
                    setattr(address, field_name, new_val)

        await db.flush()
        return address, diff

    @staticmethod
    async def delete_address(
        db: AsyncSession,
        org_id: uuid.UUID,
        contact_id: uuid.UUID,
        address_id: uuid.UUID,
    ) -> None:
        result = await db.execute(
            select(ContactAddress)
            .where(ContactAddress.id == address_id)
            .where(ContactAddress.contact_id == contact_id)
            .where(ContactAddress.organisation_id == org_id)
        )
        address = result.scalar_one_or_none()
        if not address:
            raise NotFoundError("Address not found for this contact.")
        await db.delete(address)
        await db.flush()

    # ─── Contact Notes ───────────────────────────────────────
    @staticmethod
    async def add_note(
        db: AsyncSession,
        org_id: uuid.UUID,
        contact_id: uuid.UUID,
        content: str,
        user_id: Optional[uuid.UUID] = None,
    ) -> ContactNote:
        await ContactService.get_contact(db, org_id, contact_id)
        note = ContactNote(
            organisation_id=org_id,
            contact_id=contact_id,
            content=content.strip(),
            created_by_id=user_id,
        )
        db.add(note)
        await db.flush()
        return note

    @staticmethod
    async def list_notes(
        db: AsyncSession,
        org_id: uuid.UUID,
        contact_id: uuid.UUID,
    ) -> list[ContactNoteResponse]:
        await ContactService.get_contact(db, org_id, contact_id)
        result = await db.execute(
            select(ContactNote)
            .where(ContactNote.contact_id == contact_id)
            .where(ContactNote.organisation_id == org_id)
            .options(selectinload(ContactNote.created_by))
            .order_by(ContactNote.created_at.desc())
        )
        notes = result.scalars().all()
        return [
            ContactNoteResponse(
                id=n.id,
                contact_id=n.contact_id,
                organisation_id=n.organisation_id,
                content=n.content,
                created_by_id=n.created_by_id,
                created_by_name=n.created_by.full_name or n.created_by.email if n.created_by else None,
                created_at=n.created_at,
            )
            for n in notes
        ]

    # ─── Documents / Attachments ─────────────────────────────
    @staticmethod
    async def attach_document(
        db: AsyncSession,
        org_id: uuid.UUID,
        contact_id: uuid.UUID,
        file_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> ContactDocumentResponse:
        await ContactService.get_contact(db, org_id, contact_id)

        # Cross-tenant check: ensure file belongs to the same organisation
        file_res = await db.execute(
            select(File)
            .where(File.id == file_id)
            .where(File.organisation_id == org_id)
            .where(File.is_deleted.is_(False))
        )
        file = file_res.scalar_one_or_none()
        if not file:
            raise BadRequestError("File not found or does not belong to this organisation.")

        # Check existing link
        link_res = await db.execute(
            select(FileLink)
            .where(FileLink.organisation_id == org_id)
            .where(FileLink.file_id == file_id)
            .where(FileLink.entity_type == "CONTACT")
            .where(FileLink.entity_id == contact_id)
        )
        link = link_res.scalar_one_or_none()
        if link is None:
            link = FileLink(
                organisation_id=org_id,
                file_id=file_id,
                entity_type="CONTACT",
                entity_id=contact_id,
                created_by_id=user_id,
            )
            db.add(link)
            await db.flush()

        return ContactDocumentResponse(
            id=link.id,
            file_id=file.id,
            filename=file.filename,
            content_type=file.content_type,
            size_bytes=file.size_bytes,
            created_at=link.created_at,
            created_by_id=link.created_by_id,
        )

    @staticmethod
    async def list_documents(
        db: AsyncSession,
        org_id: uuid.UUID,
        contact_id: uuid.UUID,
    ) -> list[ContactDocumentResponse]:
        await ContactService.get_contact(db, org_id, contact_id)
        result = await db.execute(
            select(FileLink, File)
            .join(File, File.id == FileLink.file_id)
            .where(FileLink.organisation_id == org_id)
            .where(FileLink.entity_type == "CONTACT")
            .where(FileLink.entity_id == contact_id)
            .where(File.is_deleted.is_(False))
            .order_by(FileLink.created_at.desc())
        )
        rows = result.all()
        return [
            ContactDocumentResponse(
                id=link.id,
                file_id=file.id,
                filename=file.filename,
                content_type=file.content_type,
                size_bytes=file.size_bytes,
                created_at=link.created_at,
                created_by_id=link.created_by_id,
            )
            for link, file in rows
        ]

    # ─── CSV Import & Export ─────────────────────────────────
    @staticmethod
    async def preview_csv(
        db: AsyncSession,
        org_id: uuid.UUID,
        file_content: str,
    ) -> ContactImportPreviewResult:
        reader = csv.DictReader(io.StringIO(file_content))
        if not reader.fieldnames:
            raise BadRequestError("CSV file is empty or missing headers.")

        # Map common headers
        field_map = {
            "name": "business_name",
            "business name": "business_name",
            "company": "business_name",
            "company name": "business_name",
            "customer": "business_name",
            "supplier": "business_name",
            "type": "contact_type",
            "contact type": "contact_type",
            "email": "email",
            "email address": "email",
            "phone": "phone",
            "telephone": "phone",
            "vat": "vat_number",
            "vat number": "vat_number",
            "company number": "company_number",
            "company reg": "company_number",
            "currency": "currency",
            "reference": "reference",
            "address": "line1",
            "address line 1": "line1",
            "city": "city",
            "country": "country_code",
            "postcode": "postcode",
        }

        normalized_headers = {h.strip().lower(): h for h in reader.fieldnames if h}

        rows: list[ContactImportRowValidation] = []
        valid_count = 0
        warning_count = 0
        error_count = 0

        for row_idx, raw_row in enumerate(reader, start=2):
            mapped_data: dict[str, Any] = {}
            for h_clean, orig_h in normalized_headers.items():
                target_field = field_map.get(h_clean)
                if target_field:
                    mapped_data[target_field] = raw_row[orig_h].strip() if raw_row[orig_h] else None

            errors = []
            warnings = []

            # Validate Business Name (Required)
            b_name = mapped_data.get("business_name")
            if not b_name:
                errors.append("Business Name is required.")

            # Validate Contact Type
            c_type = mapped_data.get("contact_type")
            if c_type:
                c_type_upper = c_type.upper()
                if c_type_upper not in ["CUSTOMER", "SUPPLIER", "BOTH"]:
                    warnings.append(f"Invalid type '{c_type}', defaulting to CUSTOMER.")
                    mapped_data["contact_type"] = "CUSTOMER"
                else:
                    mapped_data["contact_type"] = c_type_upper
            else:
                mapped_data["contact_type"] = "CUSTOMER"

            # Validate Email
            email = mapped_data.get("email")
            if email and "@" not in email:
                errors.append(f"Invalid email address '{email}'.")

            # Validate Currency
            curr = mapped_data.get("currency")
            if curr:
                if len(curr) != 3:
                    warnings.append(f"Invalid currency '{curr}', defaulting to GBP.")
                    mapped_data["currency"] = "GBP"
                else:
                    mapped_data["currency"] = curr.upper()
            else:
                mapped_data["currency"] = "GBP"

            is_valid = len(errors) == 0
            if is_valid:
                valid_count += 1
            else:
                error_count += 1
            if len(warnings) > 0:
                warning_count += 1

            rows.append(
                ContactImportRowValidation(
                    row_number=row_idx,
                    valid=is_valid,
                    errors=errors,
                    warnings=warnings,
                    data=mapped_data,
                )
            )

        return ContactImportPreviewResult(
            total_rows=len(rows),
            valid_rows=valid_count,
            warning_count=warning_count,
            error_count=error_count,
            rows=rows,
        )

    @staticmethod
    async def execute_csv_import(
        db: AsyncSession,
        org_id: uuid.UUID,
        rows: list[dict[str, Any]],
        skip_errors: bool = True,
        user_id: Optional[uuid.UUID] = None,
    ) -> tuple[int, int, list[dict[str, Any]]]:
        created_count = 0
        skipped_count = 0
        errors = []

        for idx, row in enumerate(rows, start=1):
            try:
                b_name = row.get("business_name")
                if not b_name:
                    raise ValueError("Business name is missing")

                c_type_str = row.get("contact_type", "CUSTOMER").upper()
                c_type = ContactType(c_type_str) if c_type_str in ["CUSTOMER", "SUPPLIER", "BOTH"] else ContactType.CUSTOMER

                contact = Contact(
                    organisation_id=org_id,
                    contact_type=c_type,
                    business_name=b_name.strip(),
                    email=row.get("email").strip().lower() if row.get("email") else None,
                    phone=row.get("phone").strip() if row.get("phone") else None,
                    vat_number=row.get("vat_number").strip().upper() if row.get("vat_number") else None,
                    company_number=row.get("company_number").strip().upper() if row.get("company_number") else None,
                    currency=row.get("currency", "GBP").strip().upper(),
                    reference=row.get("reference").strip() if row.get("reference") else None,
                    status=ContactStatus.ACTIVE,
                    created_by_id=user_id,
                )
                db.add(contact)
                await db.flush()

                # Add address if provided
                if row.get("line1") and row.get("city"):
                    addr = ContactAddress(
                        organisation_id=org_id,
                        contact_id=contact.id,
                        address_type=AddressType.BILLING,
                        line1=row["line1"].strip(),
                        city=row["city"].strip(),
                        postcode=row.get("postcode", "").strip().upper() or None,
                        country_code=row.get("country_code", "GB").strip().upper()[:2] or "GB",
                        is_primary=True,
                    )
                    db.add(addr)

                created_count += 1
            except Exception as e:
                skipped_count += 1
                errors.append({"row": idx, "data": row, "error": str(e)})
                if not skip_errors:
                    raise

        await db.flush()
        return created_count, skipped_count, errors

    @staticmethod
    async def export_contacts_to_csv(
        db: AsyncSession,
        org_id: uuid.UUID,
        contact_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> str:
        items, _ = await ContactService.list_contacts(
            db, org_id, contact_type=contact_type, status=status or "ALL", page=1, page_size=1000
        )
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID",
            "Type",
            "Business Name",
            "Legal Name",
            "Primary Contact",
            "Email",
            "Phone",
            "VAT Number",
            "Company Number",
            "Currency",
            "Payment Terms",
            "Status",
            "Created At",
        ])

        for c in items:
            p_contact = c.people[0].first_name + (f" {c.people[0].last_name}" if c.people[0].last_name else "") if c.people else ""
            terms_name = c.payment_terms.name if c.payment_terms else ""
            writer.writerow([
                str(c.id),
                c.contact_type.value,
                c.business_name,
                c.legal_name or "",
                p_contact,
                c.email or "",
                c.phone or "",
                c.vat_number or "",
                c.company_number or "",
                c.currency,
                terms_name,
                c.status.value,
                c.created_at.isoformat(),
            ])

        return output.getvalue()
