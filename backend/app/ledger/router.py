"""
Warp Ladger — Phase 7 Accounting Ledger Router
REST endpoints for Chart of Accounts, Journal Entries, Double-Entry Validation, Period Locking, and Trial Balance.
All endpoints enforce multi-tenancy and 8-role RBAC permissions.
"""
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import (
    CurrentUser,
    DBSession,
    OrgMembership,
    require_permission,
)
from app.database.models import AccountClass, JournalEntryStatus
from app.ledger.schemas import (
    AccountingSettingsResponse,
    AccountingSettingsUpdate,
    AccountCreate,
    AccountResponse,
    AccountUpdate,
    FinancialPeriodCreate,
    FinancialPeriodResponse,
    JournalEntryCreate,
    JournalEntryResponse,
    JournalReverseRequest,
    TrialBalanceResponse,
)
from app.ledger.service import (
    COAService,
    JournalService,
    PeriodLockService,
    TrialBalanceService,
)

accounts_router = APIRouter(
    prefix="/api/v1/organisations/{org_id}/accounts",
    tags=["Chart of Accounts"],
)

journals_router = APIRouter(
    prefix="/api/v1/organisations/{org_id}/journals",
    tags=["Journal Entries"],
)

ledger_reports_router = APIRouter(
    prefix="/api/v1/organisations/{org_id}/ledger",
    tags=["Ledger & Reports"],
)

accounting_settings_router = APIRouter(
    prefix="/api/v1/organisations/{org_id}/accounting",
    tags=["Accounting Settings & Periods"],
)


# ─── 1. Chart of Accounts Endpoints ───────────────────────────
@accounts_router.get(
    "",
    response_model=list[AccountResponse],
    dependencies=[Depends(require_permission("accounts", "read"))],
)
async def list_accounts(
    org_id: uuid.UUID,
    db: DBSession,
    account_class: Optional[AccountClass] = Query(None),
    active_only: bool = Query(True),
):
    """List Chart of Accounts with live computed balances."""
    return await COAService.list_accounts(
        db, organisation_id=org_id, account_class=account_class, active_only=active_only
    )


@accounts_router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("accounts", "create"))],
)
async def create_account(
    org_id: uuid.UUID,
    payload: AccountCreate,
    db: DBSession,
):
    """Create a new custom account in the Chart of Accounts."""
    return await COAService.create_account(db, organisation_id=org_id, data=payload)


@accounts_router.get(
    "/{account_id}",
    response_model=AccountResponse,
    dependencies=[Depends(require_permission("accounts", "read"))],
)
async def get_account(
    org_id: uuid.UUID,
    account_id: uuid.UUID,
    db: DBSession,
):
    """Get single account details."""
    acc = await COAService.get_account_by_id(db, organisation_id=org_id, account_id=account_id)
    acc_list = await COAService.list_accounts(db, organisation_id=org_id, active_only=False)
    for a in acc_list:
        if a.id == account_id:
            return a
    return acc


@accounts_router.put(
    "/{account_id}",
    response_model=AccountResponse,
    dependencies=[Depends(require_permission("accounts", "update"))],
)
async def update_account(
    org_id: uuid.UUID,
    account_id: uuid.UUID,
    payload: AccountUpdate,
    db: DBSession,
):
    """Update title, description, or active status of an account."""
    return await COAService.update_account(
        db, organisation_id=org_id, account_id=account_id, data=payload
    )


@accounts_router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("accounts", "archive"))],
)
async def archive_account(
    org_id: uuid.UUID,
    account_id: uuid.UUID,
    db: DBSession,
):
    """Archive a non-system account without posted journal history."""
    await COAService.archive_account(db, organisation_id=org_id, account_id=account_id)


# ─── 2. Journal Entries Endpoints ─────────────────────────────
@journals_router.get(
    "",
    dependencies=[Depends(require_permission("journals", "read"))],
)
async def list_journals(
    org_id: uuid.UUID,
    db: DBSession,
    status: Optional[JournalEntryStatus] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List journal entries with pagination and status/date filtering."""
    items, total = await JournalService.list_journals(
        db,
        organisation_id=org_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [
            {
                "id": j.id,
                "organisation_id": j.organisation_id,
                "entry_number": j.entry_number,
                "entry_date": j.entry_date,
                "status": j.status,
                "source_type": j.source_type,
                "source_id": j.source_id,
                "reference": j.reference,
                "narration": j.narration,
                "total_debit": j.total_debit,
                "total_credit": j.total_credit,
                "posted_at": j.posted_at,
                "posted_by_id": j.posted_by_id,
                "reversed_entry_id": j.reversed_entry_id,
                "reversal_reason": j.reversal_reason,
                "created_at": j.created_at,
                "updated_at": j.updated_at,
                "lines": [
                    {
                        "id": l.id,
                        "journal_entry_id": l.journal_entry_id,
                        "account_id": l.account_id,
                        "account_code": l.account.code if l.account else None,
                        "account_name": l.account.name if l.account else None,
                        "line_number": l.line_number,
                        "description": l.description,
                        "debit": l.debit,
                        "credit": l.credit,
                        "contact_id": l.contact_id,
                    }
                    for l in j.lines
                ],
            }
            for j in items
        ],
        "total": total,
    }


@journals_router.post(
    "",
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("journals", "create"))],
)
async def create_journal_entry(
    org_id: uuid.UUID,
    payload: JournalEntryCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Create a manual double-entry journal entry with strict sum(Dr) == sum(Cr) verification."""
    j = await JournalService.create_journal_entry(
        db, organisation_id=org_id, data=payload, user_id=current_user.id
    )
    return JournalEntryResponse(
        id=j.id,
        organisation_id=j.organisation_id,
        entry_number=j.entry_number,
        entry_date=j.entry_date,
        status=j.status,
        source_type=j.source_type,
        source_id=j.source_id,
        reference=j.reference,
        narration=j.narration,
        total_debit=j.total_debit,
        total_credit=j.total_credit,
        posted_at=j.posted_at,
        posted_by_id=j.posted_by_id,
        reversed_entry_id=j.reversed_entry_id,
        reversal_reason=j.reversal_reason,
        created_at=j.created_at,
        updated_at=j.updated_at,
        lines=[
            {
                "id": l.id,
                "journal_entry_id": l.journal_entry_id,
                "account_id": l.account_id,
                "account_code": l.account.code if l.account else None,
                "account_name": l.account.name if l.account else None,
                "line_number": l.line_number,
                "description": l.description,
                "debit": l.debit,
                "credit": l.credit,
                "contact_id": l.contact_id,
            }
            for l in j.lines
        ],
    )


@journals_router.get(
    "/{journal_id}",
    response_model=JournalEntryResponse,
    dependencies=[Depends(require_permission("journals", "read"))],
)
async def get_journal_entry(
    org_id: uuid.UUID,
    journal_id: uuid.UUID,
    db: DBSession,
):
    """Retrieve full journal details including line items."""
    j = await JournalService.get_journal_by_id(db, organisation_id=org_id, journal_id=journal_id)
    return JournalEntryResponse(
        id=j.id,
        organisation_id=j.organisation_id,
        entry_number=j.entry_number,
        entry_date=j.entry_date,
        status=j.status,
        source_type=j.source_type,
        source_id=j.source_id,
        reference=j.reference,
        narration=j.narration,
        total_debit=j.total_debit,
        total_credit=j.total_credit,
        posted_at=j.posted_at,
        posted_by_id=j.posted_by_id,
        reversed_entry_id=j.reversed_entry_id,
        reversal_reason=j.reversal_reason,
        created_at=j.created_at,
        updated_at=j.updated_at,
        lines=[
            {
                "id": l.id,
                "journal_entry_id": l.journal_entry_id,
                "account_id": l.account_id,
                "account_code": l.account.code if l.account else None,
                "account_name": l.account.name if l.account else None,
                "line_number": l.line_number,
                "description": l.description,
                "debit": l.debit,
                "credit": l.credit,
                "contact_id": l.contact_id,
            }
            for l in j.lines
        ],
    )


@journals_router.post(
    "/{journal_id}/post",
    response_model=JournalEntryResponse,
    dependencies=[Depends(require_permission("journals", "post"))],
)
async def post_draft_journal(
    org_id: uuid.UUID,
    journal_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Post a draft journal entry to the permanent general ledger."""
    j = await JournalService.post_draft_journal(
        db, organisation_id=org_id, journal_id=journal_id, user_id=current_user.id
    )
    return JournalEntryResponse(
        id=j.id,
        organisation_id=j.organisation_id,
        entry_number=j.entry_number,
        entry_date=j.entry_date,
        status=j.status,
        source_type=j.source_type,
        source_id=j.source_id,
        reference=j.reference,
        narration=j.narration,
        total_debit=j.total_debit,
        total_credit=j.total_credit,
        posted_at=j.posted_at,
        posted_by_id=j.posted_by_id,
        reversed_entry_id=j.reversed_entry_id,
        reversal_reason=j.reversal_reason,
        created_at=j.created_at,
        updated_at=j.updated_at,
        lines=[
            {
                "id": l.id,
                "journal_entry_id": l.journal_entry_id,
                "account_id": l.account_id,
                "account_code": l.account.code if l.account else None,
                "account_name": l.account.name if l.account else None,
                "line_number": l.line_number,
                "description": l.description,
                "debit": l.debit,
                "credit": l.credit,
                "contact_id": l.contact_id,
            }
            for l in j.lines
        ],
    )


@journals_router.post(
    "/{journal_id}/reverse",
    response_model=JournalEntryResponse,
    dependencies=[Depends(require_permission("journals", "reverse"))],
)
async def reverse_journal_entry(
    org_id: uuid.UUID,
    journal_id: uuid.UUID,
    payload: JournalReverseRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """Create an atomic reversing counter-entry and mark the original as REVERSED."""
    j = await JournalService.reverse_journal_entry(
        db, organisation_id=org_id, journal_id=journal_id, data=payload, user_id=current_user.id
    )
    return JournalEntryResponse(
        id=j.id,
        organisation_id=j.organisation_id,
        entry_number=j.entry_number,
        entry_date=j.entry_date,
        status=j.status,
        source_type=j.source_type,
        source_id=j.source_id,
        reference=j.reference,
        narration=j.narration,
        total_debit=j.total_debit,
        total_credit=j.total_credit,
        posted_at=j.posted_at,
        posted_by_id=j.posted_by_id,
        reversed_entry_id=j.reversed_entry_id,
        reversal_reason=j.reversal_reason,
        created_at=j.created_at,
        updated_at=j.updated_at,
        lines=[
            {
                "id": l.id,
                "journal_entry_id": l.journal_entry_id,
                "account_id": l.account_id,
                "account_code": l.account.code if l.account else None,
                "account_name": l.account.name if l.account else None,
                "line_number": l.line_number,
                "description": l.description,
                "debit": l.debit,
                "credit": l.credit,
                "contact_id": l.contact_id,
            }
            for l in j.lines
        ],
    )


# ─── 3. Trial Balance Report Endpoint ─────────────────────────
@ledger_reports_router.get(
    "/trial-balance",
    response_model=TrialBalanceResponse,
    dependencies=[Depends(require_permission("reports", "trial_balance"))],
)
async def get_trial_balance(
    org_id: uuid.UUID,
    db: DBSession,
    as_of_date: Optional[date] = Query(None),
):
    """Generate real-time balanced Trial Balance report across Chart of Accounts."""
    return await TrialBalanceService.get_trial_balance(
        db, organisation_id=org_id, as_of_date=as_of_date
    )


# ─── 4. Accounting Settings & Financial Periods ───────────────
@accounting_settings_router.get(
    "/settings",
    response_model=AccountingSettingsResponse,
    dependencies=[Depends(require_permission("periods", "read"))],
)
async def get_accounting_settings(
    org_id: uuid.UUID,
    db: DBSession,
):
    """Retrieve tenant accounting configuration and current closing lock date."""
    return await PeriodLockService.get_or_create_settings(db, organisation_id=org_id)


@accounting_settings_router.put(
    "/settings",
    response_model=AccountingSettingsResponse,
    dependencies=[Depends(require_permission("periods", "lock"))],
)
async def update_accounting_settings(
    org_id: uuid.UUID,
    payload: AccountingSettingsUpdate,
    db: DBSession,
):
    """Configure hard closing lock date and financial year end."""
    return await PeriodLockService.update_settings(
        db, organisation_id=org_id, data=payload
    )


@accounting_settings_router.get(
    "/periods",
    response_model=list[FinancialPeriodResponse],
    dependencies=[Depends(require_permission("periods", "read"))],
)
async def list_financial_periods(
    org_id: uuid.UUID,
    db: DBSession,
):
    """List financial periods and lock records."""
    return await PeriodLockService.list_periods(db, organisation_id=org_id)


@accounting_settings_router.post(
    "/periods",
    response_model=FinancialPeriodResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("periods", "lock"))],
)
async def create_financial_period(
    org_id: uuid.UUID,
    payload: FinancialPeriodCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Create or lock a specific accounting period."""
    return await PeriodLockService.create_period_lock(
        db, organisation_id=org_id, data=payload, user_id=current_user.id
    )
