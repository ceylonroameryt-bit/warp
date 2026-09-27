"""Phase 3 — Sales Invoicing: Add tax_rates, invoice_sequences, invoices, invoice_lines, invoice_deliveries

Revision ID: 0003_phase3_invoicing
Revises: 
Create Date: 2026-09-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0003_phase3_invoicing'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── tax_rates ───────────────────────────────────────────────────────────
    op.create_table(
        'tax_rates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organisation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('code', sa.String(20), nullable=False),
        sa.Column('rate', sa.Numeric(8, 4), nullable=False),
        sa.Column('tax_type', sa.Enum(
            'STANDARD', 'REDUCED', 'ZERO', 'EXEMPT', 'OUTSIDE_SCOPE',
            name='taxtype'
        ), nullable=False, server_default='STANDARD'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organisation_id', 'code', name='uq_tax_rate_org_code'),
    )
    op.create_index('ix_tax_rates_organisation_id', 'tax_rates', ['organisation_id'])

    # ── organisation_invoice_sequences ──────────────────────────────────────
    op.create_table(
        'organisation_invoice_sequences',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organisation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('prefix', sa.String(20), nullable=False, server_default='INV-'),
        sa.Column('next_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('padding', sa.Integer(), nullable=False, server_default='6'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organisation_id', 'prefix', name='uq_invoice_seq_org_prefix'),
    )

    # ── invoices ────────────────────────────────────────────────────────────
    op.create_table(
        'invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organisation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('invoice_number', sa.String(50), nullable=True),
        sa.Column('status', sa.Enum(
            'DRAFT', 'APPROVED', 'SENT', 'AWAITING_PAYMENT',
            'PARTIALLY_PAID', 'PAID', 'VOID', 'CREDITED',
            name='invoicestatus'
        ), nullable=False, server_default='DRAFT'),
        sa.Column('issue_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='GBP'),
        sa.Column('customer_reference', sa.String(100), nullable=True),
        sa.Column('purchase_order_reference', sa.String(100), nullable=True),
        sa.Column('payment_terms_id', postgresql.UUID(as_uuid=True), nullable=True),
        # Customer snapshot
        sa.Column('customer_name_snapshot', sa.String(255), nullable=True),
        sa.Column('customer_email_snapshot', sa.String(255), nullable=True),
        sa.Column('customer_vat_number_snapshot', sa.String(50), nullable=True),
        sa.Column('billing_address_snapshot', postgresql.JSONB(), nullable=True),
        # Financials — NUMERIC(19,4) — no floats
        sa.Column('subtotal', sa.Numeric(19, 4), nullable=False, server_default='0'),
        sa.Column('discount_total', sa.Numeric(19, 4), nullable=False, server_default='0'),
        sa.Column('tax_total', sa.Numeric(19, 4), nullable=False, server_default='0'),
        sa.Column('total', sa.Numeric(19, 4), nullable=False, server_default='0'),
        sa.Column('amount_paid', sa.Numeric(19, 4), nullable=False, server_default='0'),
        sa.Column('amount_due', sa.Numeric(19, 4), nullable=False, server_default='0'),
        # Notes
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('terms', sa.Text(), nullable=True),
        sa.Column('internal_notes', sa.Text(), nullable=True),
        # Workflow
        sa.Column('approved_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('voided_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('voided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('void_reason', sa.Text(), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['customer_id'], ['contacts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['payment_terms_id'], ['payment_terms.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['voided_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organisation_id', 'invoice_number', name='uq_invoice_org_number'),
    )
    op.create_index('ix_invoices_invoice_number', 'invoices', ['invoice_number'])
    op.create_index('ix_invoices_org_status', 'invoices', ['organisation_id', 'status'])
    op.create_index('ix_invoices_org_customer', 'invoices', ['organisation_id', 'customer_id'])
    op.create_index('ix_invoices_org_issue_date', 'invoices', ['organisation_id', 'issue_date'])
    op.create_index('ix_invoices_org_due_date', 'invoices', ['organisation_id', 'due_date'])
    op.create_index('ix_invoices_org_number', 'invoices', ['organisation_id', 'invoice_number'])

    # ── invoice_lines ───────────────────────────────────────────────────────
    op.create_table(
        'invoice_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organisation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tax_rate_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('quantity', sa.Numeric(19, 4), nullable=False),
        sa.Column('unit_price', sa.Numeric(19, 4), nullable=False),
        sa.Column('discount_type', sa.Enum(
            'PERCENTAGE', 'FIXED', name='discounttype'
        ), nullable=True),
        sa.Column('discount_value', sa.Numeric(19, 4), nullable=False, server_default='0'),
        sa.Column('net_amount', sa.Numeric(19, 4), nullable=False),
        sa.Column('tax_amount', sa.Numeric(19, 4), nullable=False, server_default='0'),
        sa.Column('gross_amount', sa.Numeric(19, 4), nullable=False),
        sa.Column('tax_rate_snapshot', sa.Numeric(8, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tax_rate_id'], ['tax_rates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_invoice_lines_invoice_id', 'invoice_lines', ['invoice_id'])
    op.create_index('ix_invoice_lines_org_id', 'invoice_lines', ['organisation_id'])

    # ── invoice_deliveries ──────────────────────────────────────────────────
    op.create_table(
        'invoice_deliveries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organisation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recipient_email', sa.String(255), nullable=False),
        sa.Column('cc', sa.String(500), nullable=True),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('provider_message_id', sa.String(255), nullable=True),
        sa.Column('status', sa.Enum(
            'QUEUED', 'PROCESSING', 'SENT', 'FAILED_TEMPORARY', 'FAILED',
            name='deliverystatus'
        ), nullable=False, server_default='QUEUED'),
        sa.Column('sent_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sent_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_invoice_deliveries_invoice_id', 'invoice_deliveries', ['invoice_id'])
    op.create_index('ix_invoice_deliveries_org_id', 'invoice_deliveries', ['organisation_id'])


def downgrade() -> None:
    op.drop_table('invoice_deliveries')
    op.drop_table('invoice_lines')
    op.drop_table('invoices')
    op.drop_table('organisation_invoice_sequences')
    op.drop_table('tax_rates')
    # Drop enums
    for enum_name in ('deliverystatus', 'discounttype', 'invoicestatus', 'taxtype'):
        op.execute(f'DROP TYPE IF EXISTS {enum_name}')
