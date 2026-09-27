"""Warp Ladger — Roles & Permissions Service + Seeding"""
import uuid
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError
from app.database.models import Permission, Role, RolePermission

log = structlog.get_logger(__name__)

# ─── System Permission Definitions ───────────────────────────
SYSTEM_PERMISSIONS: list[dict] = [
    {"resource": "org", "action": "read", "description": "View organisation details"},
    {"resource": "org", "action": "update", "description": "Update organisation settings"},
    {"resource": "org", "action": "delete", "description": "Delete the organisation"},
    {"resource": "member", "action": "read", "description": "View member list"},
    {"resource": "member", "action": "invite", "description": "Invite new members"},
    {"resource": "member", "action": "update", "description": "Update member roles/status"},
    {"resource": "member", "action": "remove", "description": "Remove members"},
    {"resource": "role", "action": "read", "description": "View roles"},
    {"resource": "role", "action": "create", "description": "Create custom roles"},
    {"resource": "role", "action": "update", "description": "Update roles"},
    {"resource": "role", "action": "delete", "description": "Delete custom roles"},
    {"resource": "file", "action": "read", "description": "View files"},
    {"resource": "file", "action": "upload", "description": "Upload files"},
    {"resource": "file", "action": "delete", "description": "Delete files"},
    {"resource": "audit", "action": "read", "description": "View audit log"},
    {"resource": "settings", "action": "read", "description": "View settings"},
    {"resource": "settings", "action": "update", "description": "Update settings"},
    # ── Phase 2 Contacts & Payment Terms ─────────────────────
    {"resource": "contact", "action": "read", "description": "View contacts"},
    {"resource": "contact", "action": "create", "description": "Create new contacts"},
    {"resource": "contact", "action": "update", "description": "Update contact details"},
    {"resource": "contact", "action": "archive", "description": "Archive or restore contacts"},
    {"resource": "contact", "action": "export", "description": "Export contact records to CSV"},
    {"resource": "customer", "action": "read", "description": "View customer directory"},
    {"resource": "supplier", "action": "read", "description": "View supplier directory"},
    {"resource": "contact_note", "action": "read", "description": "Read internal contact notes"},
    {"resource": "contact_note", "action": "create", "description": "Create internal contact notes"},
    {"resource": "contact_document", "action": "read", "description": "View attached contact documents"},
    {"resource": "contact_document", "action": "attach", "description": "Attach documents to contacts"},
    {"resource": "payment_terms", "action": "read", "description": "View payment terms"},
    {"resource": "payment_terms", "action": "manage", "description": "Create and update payment terms"},
    # ── Phase 3 Invoices ─────────────────────────────────
    {"resource": "invoices", "action": "read", "description": "View sales invoices"},
    {"resource": "invoices", "action": "create", "description": "Create draft invoices"},
    {"resource": "invoices", "action": "update", "description": "Edit draft invoices"},
    {"resource": "invoices", "action": "approve", "description": "Approve invoices (assign official number)"},
    {"resource": "invoices", "action": "send", "description": "Send invoices to customers"},
    {"resource": "invoices", "action": "void", "description": "Void approved invoices"},
    {"resource": "invoices", "action": "export", "description": "Export invoices to CSV or PDF"},
    # ── Phase 4 Supplier Bills ───────────────────────────
    {"resource": "bills", "action": "read", "description": "View supplier bills"},
    {"resource": "bills", "action": "create", "description": "Create draft supplier bills"},
    {"resource": "bills", "action": "update", "description": "Edit draft supplier bills"},
    {"resource": "bills", "action": "submit", "description": "Submit supplier bills for approval"},
    {"resource": "bills", "action": "approve", "description": "Approve supplier bills"},
    {"resource": "bills", "action": "reject", "description": "Reject supplier bills"},
    {"resource": "bills", "action": "void", "description": "Void approved supplier bills"},
    {"resource": "bills", "action": "export", "description": "Export supplier bills"},
    # ── Phase 5 Smart Document Capture ───────────────────
    {"resource": "documents", "action": "read", "description": "View captured documents and extraction details"},
    {"resource": "documents", "action": "process", "description": "Upload and trigger document extraction"},
    {"resource": "documents", "action": "review", "description": "Review extracted document data"},
    {"resource": "documents", "action": "correct", "description": "Correct extracted fields and classifications"},
    {"resource": "documents", "action": "retry", "description": "Retry failed document extraction"},
    {"resource": "documents", "action": "discard", "description": "Discard captured documents"},
    {"resource": "documents", "action": "create_bill", "description": "Convert extracted document into draft bill"},
    {"resource": "documents", "action": "view_extraction", "description": "View raw AI/OCR extraction and confidence scores"},
    {"resource": "documents", "action": "duplicate_override", "description": "Override duplicate document warning"},
    # ── Phase 6 Payments & Bank Accounts ─────────────────
    {"resource": "payments", "action": "read", "description": "View payments and allocations"},
    {"resource": "payments", "action": "create", "description": "Record payments and allocate to invoices/bills"},
    {"resource": "payments", "action": "update", "description": "Edit draft payments"},
    {"resource": "payments", "action": "refund", "description": "Process payment refunds"},
    {"resource": "payments", "action": "void", "description": "Void posted payments and reverse allocations"},
    {"resource": "payments", "action": "export", "description": "Export payment records"},
    {"resource": "bank_accounts", "action": "read", "description": "View bank accounts"},
    {"resource": "bank_accounts", "action": "manage", "description": "Create and manage bank accounts"},
    # ── Phase 7 Accounting Ledger & Double-Entry ─────────
    {"resource": "accounts", "action": "read", "description": "View Chart of Accounts and balances"},
    {"resource": "accounts", "action": "create", "description": "Create custom ledger accounts"},
    {"resource": "accounts", "action": "update", "description": "Edit non-system account details"},
    {"resource": "accounts", "action": "archive", "description": "Archive inactive ledger accounts"},
    {"resource": "journals", "action": "read", "description": "View journal entries and lines"},
    {"resource": "journals", "action": "create", "description": "Create manual draft journal entries"},
    {"resource": "journals", "action": "post", "description": "Post journal entries to general ledger"},
    {"resource": "journals", "action": "reverse", "description": "Create atomic reversing journal entries"},
    {"resource": "periods", "action": "read", "description": "View financial periods and lock dates"},
    {"resource": "periods", "action": "lock", "description": "Configure period lock dates and close periods"},
    {"resource": "reports", "action": "trial_balance", "description": "Generate and inspect trial balance"},
    # ── Phase 8 Financial Reporting ─────────────────────
    {"resource": "reports", "action": "view", "description": "View reporting dashboard and catalog"},
    {"resource": "reports", "action": "profit_and_loss", "description": "Generate Profit & Loss (Income Statement) report"},
    {"resource": "reports", "action": "balance_sheet", "description": "Generate Balance Sheet (Financial Position) report"},
    {"resource": "reports", "action": "aged_receivables", "description": "Generate Aged Receivables (Debtors) report"},
    {"resource": "reports", "action": "aged_payables", "description": "Generate Aged Payables (Creditors) report"},
]

# System roles and which permissions they get
SYSTEM_ROLES: list[dict] = [
    {
        "name": "owner",
        "description": "Organisation owner — full access and commercial control",
        "permissions": [f"{p['resource']}:{p['action']}" for p in SYSTEM_PERMISSIONS],
    },
    {
        "name": "administrator",
        "description": "Administrator — manages members, settings, and business operations",
        "permissions": [f"{p['resource']}:{p['action']}" for p in SYSTEM_PERMISSIONS],
    },
    {
        "name": "accountant",
        "description": "Qualified Accountant — manages financial ledgers, tax, approvals, and reports",
        "permissions": [
            "org:read", "member:read", "file:read", "file:upload", "file:delete",
            "audit:read", "settings:read",
            "contact:read", "contact:create", "contact:update", "contact:archive", "contact:export",
            "customer:read", "supplier:read", "contact_note:read", "contact_note:create",
            "contact_document:read", "contact_document:attach", "payment_terms:read", "payment_terms:manage",
            "invoices:read", "invoices:create", "invoices:update", "invoices:approve", "invoices:send", "invoices:void", "invoices:export",
            "bills:read", "bills:create", "bills:update", "bills:submit", "bills:approve", "bills:reject", "bills:void", "bills:export",
            "documents:read", "documents:process", "documents:review", "documents:correct", "documents:retry", "documents:discard",
            "documents:create_bill", "documents:view_extraction", "documents:duplicate_override",
            "payments:read", "payments:create", "payments:update", "payments:refund", "payments:void", "payments:export",
            "bank_accounts:read", "bank_accounts:manage",
            "accounts:read", "accounts:create", "accounts:update", "accounts:archive",
            "journals:read", "journals:create", "journals:post", "journals:reverse",
            "periods:read", "periods:lock",
            "reports:trial_balance", "reports:view", "reports:profit_and_loss", "reports:balance_sheet", "reports:aged_receivables", "reports:aged_payables",
        ],
    },
    {
        "name": "bookkeeper",
        "description": "Bookkeeper — transactional entry, draft invoices, bills, and document capture",
        "permissions": [
            "org:read", "member:read", "file:read", "file:upload",
            "settings:read",
            "contact:read", "contact:create", "contact:update", "contact:export",
            "customer:read", "supplier:read", "contact_note:read", "contact_note:create",
            "contact_document:read", "contact_document:attach", "payment_terms:read",
            "invoices:read", "invoices:create", "invoices:update", "invoices:send", "invoices:export",
            "bills:read", "bills:create", "bills:update", "bills:submit", "bills:export",
            "documents:read", "documents:process", "documents:review", "documents:correct", "documents:retry", "documents:create_bill", "documents:view_extraction",
            "payments:read", "payments:create", "payments:update", "payments:export",
            "bank_accounts:read",
            "accounts:read", "journals:read", "journals:create", "reports:trial_balance", "periods:read",
            "reports:view", "reports:aged_receivables", "reports:aged_payables",
        ],
    },
    {
        "name": "approver",
        "description": "Approver — reviews and authorizes supplier bills, purchase orders, and sales documents",
        "permissions": [
            "org:read", "member:read", "file:read", "settings:read",
            "contact:read", "customer:read", "supplier:read", "contact_document:read", "payment_terms:read",
            "invoices:read", "invoices:approve",
            "bills:read", "bills:approve", "bills:reject",
            "documents:read", "documents:review", "documents:view_extraction",
            "payments:read",
            "bank_accounts:read",
        ],
    },
    {
        "name": "employee",
        "description": "Employee — standard member, uploads documents, creates contact notes, drafts records",
        "permissions": [
            "org:read", "member:read",
            "file:read", "file:upload",
            "settings:read",
            "contact:read", "contact:create", "contact:update",
            "customer:read", "supplier:read",
            "contact_note:read", "contact_note:create",
            "contact_document:read", "contact_document:attach",
            "payment_terms:read",
            "invoices:read", "invoices:create",
            "bills:read", "bills:create",
            "documents:read", "documents:process",
            "payments:read",
            "bank_accounts:read",
        ],
    },
    {
        "name": "auditor",
        "description": "Auditor — independent read-only inspection of ledger, audit trails, and financial records",
        "permissions": [
            "org:read", "member:read", "role:read", "file:read", "audit:read", "settings:read",
            "contact:read", "customer:read", "supplier:read",
            "contact_note:read", "contact_document:read", "payment_terms:read",
            "invoices:read", "invoices:export",
            "bills:read", "bills:export",
            "documents:read", "documents:view_extraction",
            "payments:read", "payments:export",
            "bank_accounts:read",
            "accounts:read", "journals:read", "periods:read", "reports:trial_balance",
            "reports:view", "reports:profit_and_loss", "reports:balance_sheet", "reports:aged_receivables", "reports:aged_payables",
        ],
    },
    {
        "name": "viewer",
        "description": "Viewer — read-only visibility for executive stakeholders",
        "permissions": [
            "org:read", "member:read", "file:read", "settings:read",
            "contact:read", "customer:read", "supplier:read",
            "contact_note:read", "contact_document:read", "payment_terms:read",
            "invoices:read",
            "bills:read",
            "documents:read",
            "payments:read",
            "bank_accounts:read",
            "accounts:read", "journals:read", "periods:read", "reports:trial_balance",
            "reports:view", "reports:profit_and_loss", "reports:balance_sheet", "reports:aged_receivables", "reports:aged_payables",
        ],
    },
    # Backward compatibility aliases
    {
        "name": "admin",
        "description": "Administrator alias",
        "permissions": [f"{p['resource']}:{p['action']}" for p in SYSTEM_PERMISSIONS],
    },
    {
        "name": "member",
        "description": "Standard member alias",
        "permissions": [
            "org:read", "member:read",
            "file:read", "file:upload",
            "settings:read",
            "contact:read", "contact:create", "contact:update",
            "customer:read", "supplier:read",
            "contact_note:read", "contact_note:create",
            "contact_document:read", "contact_document:attach",
            "payment_terms:read",
            "invoices:read", "invoices:create", "invoices:update", "invoices:send",
            "bills:read", "bills:create", "bills:update", "bills:submit",
            "documents:read", "documents:process", "documents:review", "documents:correct",
            "documents:retry", "documents:discard", "documents:create_bill", "documents:view_extraction",
        ],
    },
]


async def seed_permissions_and_roles(db: AsyncSession) -> None:
    """
    Idempotent seed: create system permissions and roles.
    Safe to run multiple times.
    """
    # Create permissions
    perm_map: dict[str, Permission] = {}
    for p_def in SYSTEM_PERMISSIONS:
        name = f"{p_def['resource']}:{p_def['action']}"
        result = await db.execute(
            select(Permission).where(Permission.name == name)
        )
        perm = result.scalar_one_or_none()
        if perm is None:
            perm = Permission(
                name=name,
                resource=p_def["resource"],
                action=p_def["action"],
                description=p_def["description"],
                is_system=True,
            )
            db.add(perm)
            await db.flush()
            log.info("permission_seeded", name=name)
        perm_map[name] = perm

    # Create system roles
    for role_def in SYSTEM_ROLES:
        result = await db.execute(
            select(Role)
            .where(Role.name == role_def["name"])
            .where(Role.is_system.is_(True))
            .where(Role.organisation_id.is_(None))
        )
        role = result.scalar_one_or_none()
        if role is None:
            role = Role(
                name=role_def["name"],
                description=role_def["description"],
                is_system=True,
                organisation_id=None,
            )
            db.add(role)
            await db.flush()
            log.info("role_seeded", name=role_def["name"])

        # Assign permissions
        for perm_name in role_def["permissions"]:
            perm = perm_map.get(perm_name)
            if perm is None:
                continue
            existing_rp = await db.execute(
                select(RolePermission)
                .where(RolePermission.role_id == role.id)
                .where(RolePermission.permission_id == perm.id)
            )
            if existing_rp.scalar_one_or_none() is None:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))
                await db.flush()

    await db.commit()
    log.info("permissions_and_roles_seeded")


class RoleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_roles(self, org_id: uuid.UUID) -> list[Role]:
        """Return system roles + custom roles for the org."""
        result = await self.db.execute(
            select(Role)
            .where(
                (Role.organisation_id == org_id) | (Role.is_system.is_(True) & Role.organisation_id.is_(None))
            )
            .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
            .order_by(Role.is_system.desc(), Role.name)
        )
        return list(result.scalars().all())

    async def create_role(
        self,
        *,
        org_id: uuid.UUID,
        name: str,
        description: Optional[str] = None,
        permission_ids: list[uuid.UUID],
    ) -> Role:
        result = await self.db.execute(
            select(Role)
            .where(Role.organisation_id == org_id)
            .where(Role.name == name)
        )
        if result.scalar_one_or_none():
            raise ConflictError(f"A role named '{name}' already exists.")

        role = Role(name=name, description=description, organisation_id=org_id, is_system=False)
        self.db.add(role)
        await self.db.flush()

        for perm_id in permission_ids:
            self.db.add(RolePermission(role_id=role.id, permission_id=perm_id))
        await self.db.flush()
        return role
