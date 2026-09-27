"""Phase 4 — Supplier Bills / Money Out: Add organisation_bill_sequences, bills, bill_lines, bill_documents, bill_approval_events

Revision ID: 0004_phase4_bills
Revises: 0003_phase3_invoicing
Create Date: 2026-09-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0004_phase4_bills'
down_revision = '0003_phase3_invoicing'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── organisation_bill_sequences ─────────────────────────────────────────
    op.create_table(
        'organisation_bill_sequences',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organisation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('prefix', sa.String(20), nullable=False, server_default='BILL-'),
        sa.Column('next_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('padding', sa.Integer(), nullable=False, server_default='6'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organisation_id', 'prefix', name='uq_bill_seq_org_prefix'),
    )

    # ── bills ───────────────────────────────────────────────────────────────
    op.create_table(
        'bills',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organisation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('supplier_invoice_number', sa.String(100), nullable=False),
        sa.Column('supplier_invoice_number_normalized', sa.String(100), nullable=False),
        sa.Column('internal_bill_number', sa.String(50), nullable=True),
        sa.Column('status', sa.Enum(
            'DRAFT', 'AWAITING_APPROVAL', 'APPROVED', 'AWAITING_PAYMENT',
            'PARTIALLY_PAID', 'PAID', 'REJECTED', 'VOID',
            name='billstatus'
        ), nullable=False, server_default='DRAFT'),
        sa.Column('bill_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='GBP'),
        sa.Column('supplier_reference', sa.String(100), nullable=True),
        sa.Column('purchase_order_reference', sa.String(100), nullable=True),
        sa.Column('payment_terms_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('expense_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('purchase_category_id', sa.String(100), nullable=True),
        # Supplier snapshot
        sa.Column('supplier_name_snapshot', sa.String(255), nullable=True),
        sa.Column('supplier_email_snapshot', sa.String(255), nullable=True),
        sa.Column('supplier_vat_number_snapshot', sa.String(50), nullable=True),
        sa.Column('supplier_address_snapshot', postgresql.JSONB(), nullable=True),
        # Financials (NUMERIC 19,4)
        sa.Column('subtotal', sa.Numeric(19, 4), nullable=False, server_default='0'),
        sa.Column('discount_total', sa.Numeric(19, 4), nullable=False, server_default='0'),
        sa.Column('tax_total', sa.Numeric(19, 4), nullable=False, server_default='0'),
        sa.Column('total', sa.Numeric(19, 4), nullable=False, server_default='0'),
        sa.Column('amount_paid', sa.Numeric(19, 4), nullable=False, server_default='0'),
        sa.Column('amount_due', sa.Numeric(19, 4), nullable=False, server_default='0'),
        # Notes
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('internal_notes', sa.Text(), nullable=True),
        # Workflow
        sa.Column('submitted_for_approval_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('submitted_for_approval_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('voided_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('voided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('void_reason', sa.Text(), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        # Optimistic locking
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        # Duplicate override
        sa.Column('duplicate_override_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('duplicate_override_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duplicate_override_reason', sa.Text(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['contacts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['payment_terms_id'], ['payment_terms.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['submitted_for_approval_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['rejected_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['voided_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['duplicate_override_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organisation_id', 'internal_bill_number', name='uq_bill_org_internal_number'),
    )
    op.create_index('ix_bills_org_status', 'bills', ['organisation_id', 'status'])
    op.create_index('ix_bills_org_supplier', 'bills', ['organisation_id', 'supplier_id'])
    op.create_index('ix_bills_org_bill_date', 'bills', ['organisation_id', 'bill_date'])
    op.create_index('ix_bills_org_due_date', 'bills', ['organisation_id', 'due_date'])
    op.create_index('ix_bills_org_supplier_inv_norm', 'bills', ['organisation_id', 'supplier_invoice_number_normalized'])
    op.create_index('ix_bills_org_internal_number', 'bills', ['organisation_id', 'internal_bill_number'])

    # ── bill_lines ──────────────────────────────────────────────────────────
    op.create_table(
        'bill_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organisation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tax_rate_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('quantity', sa.Numeric(19, 4), nullable=False),
        sa.Column('unit_price', sa.Numeric(19, 4), nullable=False),
        sa.Column('discount_type', sa.Enum('PERCENTAGE', 'FIXED', name='discounttype'), nullable=True),
        sa.Column('discount_value', sa.Numeric(19, 4), nullable=False, server_default='0'),
        sa.Column('net_amount', sa.Numeric(19, 4), nullable=False),
        sa.Column('tax_amount', sa.Numeric(19, 4), nullable=False, server_default='0'),
        sa.Column('gross_amount', sa.Numeric(19, 4), nullable=False),
        sa.Column('tax_rate_snapshot', sa.Numeric(8, 4), nullable=True),
        sa.Column('expense_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('purchase_category', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['bill_id'], ['bills.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tax_rate_id'], ['tax_rates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_bill_lines_bill_id', 'bill_lines', ['bill_id'])
    op.create_index('ix_bill_lines_org_id', 'bill_lines', ['organisation_id'])

    # ── bill_documents ──────────────────────────────────────────────────────
    op.create_table(
        'bill_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organisation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_type', sa.String(50), nullable=False, server_default='ORIGINAL_INVOICE'),
        sa.Column('checksum_sha256', sa.String(64), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['bill_id'], ['bills.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_bill_documents_bill_id', 'bill_documents', ['bill_id'])
    op.create_index('ix_bill_documents_org_id', 'bill_documents', ['organisation_id'])
    op.create_index('ix_bill_documents_checksum', 'bill_documents', ['organisation_id', 'checksum_sha256'])

    # ── bill_approval_events ────────────────────────────────────────────────
    op.create_table(
        'bill_approval_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organisation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.Enum(
            'SUBMITTED', 'APPROVED', 'REJECTED', 'RESUBMITTED',
            name='billapprovalaction'
        ), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['bill_id'], ['bills.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_bill_approval_events_bill_id', 'bill_approval_events', ['bill_id'])
    op.create_index('ix_bill_approval_events_org_id', 'bill_approval_events', ['organisation_id'])


def downgrade() -> None:
    op.drop_table('bill_approval_events')
    op.drop_table('bill_documents')
    op.drop_table('bill_lines')
    op.drop_table('bills')
    op.drop_table('organisation_bill_sequences')
    op.execute("DROP TYPE IF EXISTS billapprovalaction")
    op.execute("DROP TYPE IF EXISTS billstatus")
