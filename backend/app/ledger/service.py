"""
Warp Ladger — Phase 7 Accounting Ledger Service
Chart of Accounts, Concurrency-Safe Journal Sequence, Double-Entry Balance, Immutability, Period Locks, and Trial Balance.
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    NotFoundError,
    PermissionDeniedError,
    ValidationFailedError,
    WarpLadgerError,
)
from app.database.models import (
    Account,
    AccountClass,
    AccountSubtype,
    FinancialPeriod,
    JournalEntry,
    JournalEntryStatus,
    JournalLine,
    JournalSourceType,
    Organisation,
    OrganisationAccountingSettings,
    OrganisationJournalSequence,
)
from app.ledger.schemas import (
    AccountingSettingsUpdate,
    AccountCreate,
    AccountUpdate,
    FinancialPeriodCreate,
    JournalEntryCreate,
    JournalReverseRequest,
    TrialBalanceAccountItem,
    TrialBalanceResponse,
)

UTC = timezone.utc


class ImmutableLedgerError(WarpLadgerError):
    """Raised when an attempt is made to edit or delete a posted financial record."""
    status_code = 409
    error_code = "IMMUTABLE_RECORD"


class PeriodLockedError(WarpLadgerError):
    """Raised when an operation falls into a closed or locked financial period."""
    status_code = 422
    error_code = "PERIOD_LOCKED"


# ─── Standard UK GAAP Chart of Accounts Template ──────────────
DEFAULT_COA_TEMPLATE = [
    # ── 1000 - 1999: Assets ───────────────────────────────────
    {"code": "1000", "name": "Bank Current Account", "account_class": AccountClass.ASSET, "account_subtype": AccountSubtype.CURRENT_ASSET.value, "is_system": True, "description": "Primary operational clearing bank account"},
    {"code": "1010", "name": "Petty Cash", "account_class": AccountClass.ASSET, "account_subtype": AccountSubtype.CURRENT_ASSET.value, "is_system": False, "description": "Cash on hand"},
    {"code": "1200", "name": "Accounts Receivable", "account_class": AccountClass.ASSET, "account_subtype": AccountSubtype.CURRENT_ASSET.value, "is_system": True, "description": "Sales ledger trade debtors control account"},
    {"code": "1500", "name": "Office Equipment", "account_class": AccountClass.ASSET, "account_subtype": AccountSubtype.FIXED_ASSET.value, "is_system": False, "description": "Tangible fixed capital assets"},
    # ── 2000 - 2999: Liabilities ──────────────────────────────
    {"code": "2000", "name": "Accounts Payable", "account_class": AccountClass.LIABILITY, "account_subtype": AccountSubtype.CURRENT_LIABILITY.value, "is_system": True, "description": "Purchase ledger trade creditors control account"},
    {"code": "2200", "name": "VAT Output Tax", "account_class": AccountClass.LIABILITY, "account_subtype": AccountSubtype.CURRENT_LIABILITY.value, "is_system": True, "description": "Sales VAT collected on behalf of tax authority"},
    {"code": "2210", "name": "VAT Input Tax", "account_class": AccountClass.LIABILITY, "account_subtype": AccountSubtype.CURRENT_LIABILITY.value, "is_system": True, "description": "Purchase VAT reclaimable from tax authority"},
    {"code": "2220", "name": "PAYE / NIC Payable", "account_class": AccountClass.LIABILITY, "account_subtype": AccountSubtype.CURRENT_LIABILITY.value, "is_system": False, "description": "Payroll withholdings payable to revenue service"},
    # ── 3000 - 3999: Equity ───────────────────────────────────
    {"code": "3000", "name": "Retained Earnings", "account_class": AccountClass.EQUITY, "account_subtype": AccountSubtype.EQUITY.value, "is_system": True, "description": "Cumulative historical net profit/loss retained"},
    {"code": "3010", "name": "Owner Capital / Ordinary Shares", "account_class": AccountClass.EQUITY, "account_subtype": AccountSubtype.EQUITY.value, "is_system": False, "description": "Initial capital invested by equity owners"},
    # ── 4000 - 4999: Revenue ──────────────────────────────────
    {"code": "4000", "name": "Sales Revenue", "account_class": AccountClass.REVENUE, "account_subtype": AccountSubtype.OPERATING_REVENUE.value, "is_system": True, "description": "Core operating revenue from sale of goods/services"},
    {"code": "4100", "name": "Consulting & Services Revenue", "account_class": AccountClass.REVENUE, "account_subtype": AccountSubtype.OPERATING_REVENUE.value, "is_system": False, "description": "Professional services fees"},
    {"code": "4900", "name": "Other Income", "account_class": AccountClass.REVENUE, "account_subtype": AccountSubtype.OTHER_INCOME.value, "is_system": False, "description": "Interest and sundry ancillary income"},
    # ── 5000 - 9999: Expenses ─────────────────────────────────
    {"code": "5000", "name": "Cost of Goods Sold (COGS)", "account_class": AccountClass.EXPENSE, "account_subtype": AccountSubtype.COST_OF_SALES.value, "is_system": False, "description": "Direct costs attributable to production of sold goods"},
    {"code": "6000", "name": "Advertising & Marketing", "account_class": AccountClass.EXPENSE, "account_subtype": AccountSubtype.OVERHEAD.value, "is_system": False, "description": "Brand promotion, campaigns, and ad spend"},
    {"code": "6100", "name": "Rent & Premises", "account_class": AccountClass.EXPENSE, "account_subtype": AccountSubtype.OVERHEAD.value, "is_system": False, "description": "Office lease and premises costs"},
    {"code": "6200", "name": "Utilities & Telecommunications", "account_class": AccountClass.EXPENSE, "account_subtype": AccountSubtype.OVERHEAD.value, "is_system": False, "description": "Power, heating, broadband, and phone services"},
    {"code": "6300", "name": "Software & Subscriptions", "account_class": AccountClass.EXPENSE, "account_subtype": AccountSubtype.OVERHEAD.value, "is_system": False, "description": "Cloud hosting, SaaS tooling, and IT licences"},
    {"code": "6400", "name": "Travel & Entertainment", "account_class": AccountClass.EXPENSE, "account_subtype": AccountSubtype.OVERHEAD.value, "is_system": False, "description": "Business travel, lodging, and client meals"},
    {"code": "6500", "name": "Professional & Legal Fees", "account_class": AccountClass.EXPENSE, "account_subtype": AccountSubtype.OVERHEAD.value, "is_system": False, "description": "Legal counsel, external accounting, and compliance audit"},
    {"code": "6900", "name": "Bank Charges & Interest", "account_class": AccountClass.EXPENSE, "account_subtype": AccountSubtype.OVERHEAD.value, "is_system": False, "description": "Merchant processing fees and bank transaction tariffs"},
]


# ─── 1. Chart of Accounts Service ─────────────────────────────
class COAService:
    @staticmethod
    async def ensure_default_accounts(db: AsyncSession, organisation_id: uuid.UUID) -> list[Account]:
        """Automatically seed standard UK GAAP accounts if tenant COA is empty."""
        stmt = select(Account).where(Account.organisation_id == organisation_id).limit(1)
        res = await db.execute(stmt)
        if res.scalars().first():
            return []

        seeded = []
        for item in DEFAULT_COA_TEMPLATE:
            acc = Account(
                organisation_id=organisation_id,
                code=item["code"],
                name=item["name"],
                account_class=item["account_class"],
                account_subtype=item["account_subtype"],
                currency="GBP",
                is_system=item["is_system"],
                active=True,
                description=item["description"],
            )
            db.add(acc)
            seeded.append(acc)

        await db.flush()
        return seeded

    @staticmethod
    async def list_accounts(
        db: AsyncSession,
        organisation_id: uuid.UUID,
        account_class: Optional[AccountClass] = None,
        active_only: bool = True,
    ) -> list[Account]:
        await COAService.ensure_default_accounts(db, organisation_id)

        query = select(Account).where(Account.organisation_id == organisation_id)
        if account_class:
            query = query.where(Account.account_class == account_class)
        if active_only:
            query = query.where(Account.active == True)

        query = query.order_by(Account.code.asc())
        res = await db.execute(query)
        accounts = list(res.scalars().all())

        # Compute running balances for all accounts from posted journal lines
        bal_query = (
            select(
                JournalLine.account_id,
                func.coalesce(func.sum(JournalLine.debit), 0).label("total_dr"),
                func.coalesce(func.sum(JournalLine.credit), 0).label("total_cr"),
            )
            .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
            .where(
                JournalEntry.organisation_id == organisation_id,
                JournalEntry.status == JournalEntryStatus.POSTED,
            )
            .group_by(JournalLine.account_id)
        )
        bal_res = await db.execute(bal_query)
        balances = {row.account_id: (Decimal(str(row.total_dr)), Decimal(str(row.total_cr))) for row in bal_res.all()}

        for acc in accounts:
            dr, cr = balances.get(acc.id, (Decimal("0.0000"), Decimal("0.0000")))
            if acc.account_class in (AccountClass.ASSET, AccountClass.EXPENSE):
                acc.current_balance = (dr - cr).quantize(Decimal("0.0001"))
            else:
                acc.current_balance = (cr - dr).quantize(Decimal("0.0001"))

        return accounts

    @staticmethod
    async def get_account_by_id(db: AsyncSession, organisation_id: uuid.UUID, account_id: uuid.UUID) -> Account:
        stmt = select(Account).where(Account.organisation_id == organisation_id, Account.id == account_id)
        res = await db.execute(stmt)
        acc = res.scalars().first()
        if not acc:
            raise NotFoundError(f"Account '{account_id}' not found")
        return acc

    @staticmethod
    async def create_account(db: AsyncSession, organisation_id: uuid.UUID, data: AccountCreate) -> Account:
        # Check uniqueness of code
        stmt = select(Account).where(Account.organisation_id == organisation_id, Account.code == data.code.strip())
        res = await db.execute(stmt)
        if res.scalars().first():
            raise ValidationFailedError(f"Account code '{data.code}' already exists for this organisation.")

        acc = Account(
            organisation_id=organisation_id,
            code=data.code.strip(),
            name=data.name.strip(),
            account_class=data.account_class,
            account_subtype=data.account_subtype.strip(),
            currency=data.currency.upper(),
            is_system=False,
            active=True,
            description=data.description.strip() if data.description else None,
        )
        db.add(acc)
        await db.commit()
        await db.refresh(acc)
        acc.current_balance = Decimal("0.0000")
        return acc

    @staticmethod
    async def update_account(db: AsyncSession, organisation_id: uuid.UUID, account_id: uuid.UUID, data: AccountUpdate) -> Account:
        acc = await COAService.get_account_by_id(db, organisation_id, account_id)
        if data.name is not None:
            acc.name = data.name.strip()
        if data.account_subtype is not None:
            acc.account_subtype = data.account_subtype.strip()
        if data.description is not None:
            acc.description = data.description.strip() or None
        if data.active is not None:
            if acc.is_system and not data.active:
                raise ValidationFailedError("System accounts cannot be deactivated.")
            acc.active = data.active

        await db.commit()
        await db.refresh(acc)
        return acc

    @staticmethod
    async def archive_account(db: AsyncSession, organisation_id: uuid.UUID, account_id: uuid.UUID) -> None:
        acc = await COAService.get_account_by_id(db, organisation_id, account_id)
        if acc.is_system:
            raise ValidationFailedError("Core system account cannot be archived or deleted.")

        # Check if account has any posted journal lines
        line_check = await db.execute(
            select(func.count(JournalLine.id))
            .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
            .where(
                JournalLine.account_id == account_id,
                JournalEntry.status == JournalEntryStatus.POSTED,
            )
        )
        if line_check.scalar_one() > 0:
            raise ValidationFailedError("Cannot delete an account with posted journal history. Deactivate it instead.")

        acc.active = False
        await db.commit()


# ─── 2. Journal Sequence Service ──────────────────────────────
class JournalSequenceService:
    @staticmethod
    async def get_next_journal_number(db: AsyncSession, organisation_id: uuid.UUID) -> str:
        """Pessimistic lock on sequence row to produce JRN-000001 with zero race conditions."""
        stmt = (
            select(OrganisationJournalSequence)
            .where(OrganisationJournalSequence.organisation_id == organisation_id)
            .with_for_update()
        )
        res = await db.execute(stmt)
        seq = res.scalars().first()

        if not seq:
            seq = OrganisationJournalSequence(
                organisation_id=organisation_id,
                prefix="JRN-",
                next_number=1,
                padding=6,
            )
            db.add(seq)
            await db.flush()

        number_str = f"{seq.prefix}{seq.next_number:0{seq.padding}d}"
        seq.next_number += 1
        return number_str


# ─── 3. Period Lock Service ───────────────────────────────────
class PeriodLockService:
    @staticmethod
    async def get_or_create_settings(db: AsyncSession, organisation_id: uuid.UUID) -> OrganisationAccountingSettings:
        stmt = select(OrganisationAccountingSettings).where(
            OrganisationAccountingSettings.organisation_id == organisation_id
        )
        res = await db.execute(stmt)
        settings = res.scalars().first()
        if not settings:
            settings = OrganisationAccountingSettings(
                organisation_id=organisation_id,
                financial_year_end_day=31,
                financial_year_end_month=12,
                lock_date=None,
            )
            db.add(settings)
            await db.flush()
        return settings

    @staticmethod
    async def update_settings(
        db: AsyncSession, organisation_id: uuid.UUID, data: AccountingSettingsUpdate
    ) -> OrganisationAccountingSettings:
        settings = await PeriodLockService.get_or_create_settings(db, organisation_id)
        if data.financial_year_end_day is not None:
            settings.financial_year_end_day = data.financial_year_end_day
        if data.financial_year_end_month is not None:
            settings.financial_year_end_month = data.financial_year_end_month
        if data.lock_date is not None:
            settings.lock_date = data.lock_date

        await db.commit()
        await db.refresh(settings)
        return settings

    @staticmethod
    async def check_date_locked(db: AsyncSession, organisation_id: uuid.UUID, tx_date: date) -> None:
        """Enforces that transaction date does not violate global lock date or locked financial periods."""
        settings = await PeriodLockService.get_or_create_settings(db, organisation_id)
        if settings.lock_date and tx_date <= settings.lock_date:
            raise PeriodLockedError(
                f"Transaction date {tx_date} falls on or before locked accounting closing date {settings.lock_date}."
            )

        # Check locked financial periods
        stmt = select(FinancialPeriod).where(
            FinancialPeriod.organisation_id == organisation_id,
            FinancialPeriod.is_locked == True,
            FinancialPeriod.start_date <= tx_date,
            FinancialPeriod.end_date >= tx_date,
        )
        res = await db.execute(stmt)
        locked_p = res.scalars().first()
        if locked_p:
            raise PeriodLockedError(
                f"Transaction date {tx_date} falls inside locked financial period '{locked_p.period_name}'."
            )

    @staticmethod
    async def create_period_lock(
        db: AsyncSession, organisation_id: uuid.UUID, data: FinancialPeriodCreate, user_id: uuid.UUID
    ) -> FinancialPeriod:
        if data.start_date > data.end_date:
            raise ValidationFailedError("Period start date cannot be after end date.")

        stmt = select(FinancialPeriod).where(
            FinancialPeriod.organisation_id == organisation_id,
            FinancialPeriod.period_name == data.period_name.strip(),
        )
        res = await db.execute(stmt)
        if res.scalars().first():
            raise ValidationFailedError(f"Period with name '{data.period_name}' already exists.")

        period = FinancialPeriod(
            organisation_id=organisation_id,
            period_name=data.period_name.strip(),
            start_date=data.start_date,
            end_date=data.end_date,
            is_locked=data.is_locked,
            locked_at=datetime.now(UTC) if data.is_locked else None,
            locked_by_id=user_id if data.is_locked else None,
            lock_reason=data.lock_reason.strip() if data.lock_reason else None,
        )
        db.add(period)
        await db.commit()
        await db.refresh(period)
        return period

    @staticmethod
    async def list_periods(db: AsyncSession, organisation_id: uuid.UUID) -> list[FinancialPeriod]:
        stmt = (
            select(FinancialPeriod)
            .where(FinancialPeriod.organisation_id == organisation_id)
            .order_by(FinancialPeriod.start_date.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


# ─── 4. Double-Entry Journal Service ──────────────────────────
class JournalService:
    @staticmethod
    async def create_journal_entry(
        db: AsyncSession,
        organisation_id: uuid.UUID,
        data: JournalEntryCreate,
        user_id: Optional[uuid.UUID] = None,
    ) -> JournalEntry:
        # 1. Period Lock Check
        await PeriodLockService.check_date_locked(db, organisation_id, data.entry_date)

        # 2. Double-Entry Invariant: sum(debit) == sum(credit) > 0
        total_dr = sum(Decimal(str(l.debit)) for l in data.lines).quantize(Decimal("0.0001"))
        total_cr = sum(Decimal(str(l.credit)) for l in data.lines).quantize(Decimal("0.0001"))
        if total_dr <= Decimal("0.0000") or total_cr <= Decimal("0.0000"):
            raise ValidationFailedError("Journal totals must be strictly greater than zero.")
        if total_dr != total_cr:
            raise ValidationFailedError(
                f"Double-entry equation violated: total debits ({total_dr}) != total credits ({total_cr})."
            )

        # 3. Validate accounts belong to tenant and are active
        account_ids = {l.account_id for l in data.lines}
        acc_stmt = select(Account).where(
            Account.organisation_id == organisation_id,
            Account.id.in_(account_ids),
            Account.active == True,
        )
        acc_res = await db.execute(acc_stmt)
        valid_accounts = {a.id: a for a in acc_res.scalars().all()}
        if len(valid_accounts) != len(account_ids):
            raise ValidationFailedError("One or more specified accounts do not exist, belong to another tenant, or are inactive.")

        # 4. Generate official sequential journal number
        entry_number = await JournalSequenceService.get_next_journal_number(db, organisation_id)

        now = datetime.now(UTC)
        is_posted = data.post_immediately
        status = JournalEntryStatus.POSTED if is_posted else JournalEntryStatus.DRAFT

        journal = JournalEntry(
            organisation_id=organisation_id,
            entry_number=entry_number,
            entry_date=data.entry_date,
            status=status,
            source_type=data.source_type,
            source_id=data.source_id,
            reference=data.reference.strip() if data.reference else None,
            narration=data.narration.strip() if data.narration else None,
            total_debit=total_dr,
            total_credit=total_cr,
            posted_at=now if is_posted else None,
            posted_by_id=user_id if is_posted else None,
        )
        db.add(journal)
        await db.flush()

        # 5. Add Journal Lines
        for idx, line_data in enumerate(data.lines, 1):
            line = JournalLine(
                journal_entry_id=journal.id,
                account_id=line_data.account_id,
                line_number=idx,
                description=line_data.description.strip() if line_data.description else None,
                debit=Decimal(str(line_data.debit)).quantize(Decimal("0.0001")),
                credit=Decimal(str(line_data.credit)).quantize(Decimal("0.0001")),
                contact_id=line_data.contact_id,
            )
            db.add(line)

        await db.commit()
        return await JournalService.get_journal_by_id(db, organisation_id, journal.id)

    @staticmethod
    async def get_journal_by_id(db: AsyncSession, organisation_id: uuid.UUID, journal_id: uuid.UUID) -> JournalEntry:
        stmt = (
            select(JournalEntry)
            .options(selectinload(JournalEntry.lines).joinedload(JournalLine.account))
            .where(JournalEntry.organisation_id == organisation_id, JournalEntry.id == journal_id)
        )
        res = await db.execute(stmt)
        entry = res.scalars().first()
        if not entry:
            raise NotFoundError(f"JournalEntry '{journal_id}' not found")
        return entry

    @staticmethod
    async def list_journals(
        db: AsyncSession,
        organisation_id: uuid.UUID,
        status: Optional[JournalEntryStatus] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[JournalEntry], int]:
        query = (
            select(JournalEntry)
            .options(selectinload(JournalEntry.lines).joinedload(JournalLine.account))
            .where(JournalEntry.organisation_id == organisation_id)
        )
        if status:
            query = query.where(JournalEntry.status == status)
        if from_date:
            query = query.where(JournalEntry.entry_date >= from_date)
        if to_date:
            query = query.where(JournalEntry.entry_date <= to_date)

        count_query = select(func.count(JournalEntry.id)).where(JournalEntry.organisation_id == organisation_id)
        if status:
            count_query = count_query.where(JournalEntry.status == status)
        if from_date:
            count_query = count_query.where(JournalEntry.entry_date >= from_date)
        if to_date:
            count_query = count_query.where(JournalEntry.entry_date <= to_date)

        total_res = await db.execute(count_query)
        total = total_res.scalar_one()

        query = query.order_by(JournalEntry.entry_date.desc(), JournalEntry.entry_number.desc()).limit(limit).offset(offset)
        items = list((await db.execute(query)).scalars().all())
        return items, total

    @staticmethod
    async def post_draft_journal(
        db: AsyncSession, organisation_id: uuid.UUID, journal_id: uuid.UUID, user_id: uuid.UUID
    ) -> JournalEntry:
        stmt = (
            select(JournalEntry)
            .options(selectinload(JournalEntry.lines))
            .where(JournalEntry.organisation_id == organisation_id, JournalEntry.id == journal_id)
            .with_for_update()
        )
        res = await db.execute(stmt)
        entry = res.scalars().first()
        if not entry:
            raise NotFoundError(f"JournalEntry '{journal_id}' not found")

        if entry.status != JournalEntryStatus.DRAFT:
            raise ValidationFailedError(f"Cannot post journal with status '{entry.status}'.")

        await PeriodLockService.check_date_locked(db, organisation_id, entry.entry_date)

        entry.status = JournalEntryStatus.POSTED
        entry.posted_at = datetime.now(UTC)
        entry.posted_by_id = user_id

        await db.commit()
        return await JournalService.get_journal_by_id(db, organisation_id, entry.id)

    @staticmethod
    async def reverse_journal_entry(
        db: AsyncSession,
        organisation_id: uuid.UUID,
        journal_id: uuid.UUID,
        data: JournalReverseRequest,
        user_id: uuid.UUID,
    ) -> JournalEntry:
        """Atomic double-entry reversal. Swaps debits and credits and links counter-entry."""
        stmt = (
            select(JournalEntry)
            .options(selectinload(JournalEntry.lines))
            .where(JournalEntry.organisation_id == organisation_id, JournalEntry.id == journal_id)
            .with_for_update()
        )
        res = await db.execute(stmt)
        original = res.scalars().first()
        if not original:
            raise NotFoundError(f"JournalEntry '{journal_id}' not found")

        if original.status != JournalEntryStatus.POSTED:
            raise ValidationFailedError(
                f"Only POSTED journals can be reversed. Current status is '{original.status}'."
            )

        rev_date = data.reversal_date or date.today()
        await PeriodLockService.check_date_locked(db, organisation_id, rev_date)

        rev_number = await JournalSequenceService.get_next_journal_number(db, organisation_id)
        now = datetime.now(UTC)

        reversal_journal = JournalEntry(
            organisation_id=organisation_id,
            entry_number=rev_number,
            entry_date=rev_date,
            status=JournalEntryStatus.POSTED,
            source_type=JournalSourceType.REVERSAL,
            source_id=original.id,
            reference=f"Reversal of {original.entry_number}",
            narration=f"Reversal: {data.reversal_reason.strip()}",
            total_debit=original.total_credit,
            total_credit=original.total_debit,
            posted_at=now,
            posted_by_id=user_id,
            reversed_entry_id=original.id,
            reversal_reason=data.reversal_reason.strip(),
        )
        db.add(reversal_journal)
        await db.flush()

        # Invert debits and credits
        for idx, line in enumerate(original.lines, 1):
            rev_line = JournalLine(
                journal_entry_id=reversal_journal.id,
                account_id=line.account_id,
                line_number=idx,
                description=f"Reversal of line {idx}: {line.description or ''}".strip(),
                debit=line.credit,
                credit=line.debit,
                contact_id=line.contact_id,
            )
            db.add(rev_line)

        # Mark original as REVERSED
        original.status = JournalEntryStatus.REVERSED
        original.reversed_entry_id = reversal_journal.id
        original.reversal_reason = data.reversal_reason.strip()

        await db.commit()
        return await JournalService.get_journal_by_id(db, organisation_id, reversal_journal.id)


# ─── 5. Trial Balance Reporting Service ───────────────────────
class TrialBalanceService:
    @staticmethod
    async def get_trial_balance(
        db: AsyncSession, organisation_id: uuid.UUID, as_of_date: Optional[date] = None
    ) -> TrialBalanceResponse:
        """Real-time calculation of net debit/credit balance across Chart of Accounts."""
        effective_date = as_of_date or date.today()
        await COAService.ensure_default_accounts(db, organisation_id)

        # Query all active accounts
        acc_stmt = select(Account).where(
            Account.organisation_id == organisation_id,
            Account.active == True,
        ).order_by(Account.code.asc())
        accounts = list((await db.execute(acc_stmt)).scalars().all())

        # Sum debits and credits from posted journal lines as of date
        bal_stmt = (
            select(
                JournalLine.account_id,
                func.coalesce(func.sum(JournalLine.debit), 0).label("sum_dr"),
                func.coalesce(func.sum(JournalLine.credit), 0).label("sum_cr"),
            )
            .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
            .where(
                JournalEntry.organisation_id == organisation_id,
                JournalEntry.status == JournalEntryStatus.POSTED,
                JournalEntry.entry_date <= effective_date,
            )
            .group_by(JournalLine.account_id)
        )
        bal_res = await db.execute(bal_stmt)
        totals = {row.account_id: (Decimal(str(row.sum_dr)), Decimal(str(row.sum_cr))) for row in bal_res.all()}

        items: list[TrialBalanceAccountItem] = []
        grand_total_dr = Decimal("0.0000")
        grand_total_cr = Decimal("0.0000")

        for acc in accounts:
            raw_dr, raw_cr = totals.get(acc.id, (Decimal("0.0000"), Decimal("0.0000")))
            if raw_dr == 0 and raw_cr == 0:
                continue

            # Standard accounting net balance determination
            if acc.account_class in (AccountClass.ASSET, AccountClass.EXPENSE):
                net = (raw_dr - raw_cr).quantize(Decimal("0.0001"))
                if net >= 0:
                    dr_bal = net
                    cr_bal = Decimal("0.0000")
                else:
                    dr_bal = Decimal("0.0000")
                    cr_bal = (-net).quantize(Decimal("0.0001"))
            else:
                # Liability, Equity, Revenue (Normal credit)
                net = (raw_cr - raw_dr).quantize(Decimal("0.0001"))
                if net >= 0:
                    cr_bal = net
                    dr_bal = Decimal("0.0000")
                else:
                    cr_bal = Decimal("0.0000")
                    dr_bal = (-net).quantize(Decimal("0.0001"))

            items.append(
                TrialBalanceAccountItem(
                    account_id=acc.id,
                    account_code=acc.code,
                    account_name=acc.name,
                    account_class=acc.account_class,
                    account_subtype=acc.account_subtype,
                    debit_balance=dr_bal,
                    credit_balance=cr_bal,
                )
            )
            grand_total_dr += dr_bal
            grand_total_cr += cr_bal

        grand_total_dr = grand_total_dr.quantize(Decimal("0.0001"))
        grand_total_cr = grand_total_cr.quantize(Decimal("0.0001"))
        is_balanced = grand_total_dr == grand_total_cr

        return TrialBalanceResponse(
            as_of_date=effective_date,
            currency="GBP",
            accounts=items,
            total_debit=grand_total_dr,
            total_credit=grand_total_cr,
            is_balanced=is_balanced,
        )
