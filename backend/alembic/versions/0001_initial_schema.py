"""Initial Finance4Dummies schema with TimescaleDB hypertables

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-23 15:30:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")

    # 1. Identity
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=True),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_refresh_tokens_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_expires", "refresh_tokens", ["user_id", "expires_at"])

    # 2. Banking Actors & Accounts
    op.create_table(
        "institutions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("institution_type", sa.String(length=32), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("color_hex", sa.String(length=7), nullable=True),
        sa.Column("logo_key", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_institutions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_institutions"),
    )
    op.create_index("ix_institutions_user_name", "institutions", ["user_id", "name"])

    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("account_type", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("initial_balance", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("initial_balance_date", sa.Date(), nullable=False),
        sa.Column("iban_last4", sa.String(length=4), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_accounts_institution_id_institutions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_accounts_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_accounts"),
    )
    op.create_index("ix_accounts_user_institution", "accounts", ["user_id", "institution_id"])
    op.create_index("ix_accounts_user_type", "accounts", ["user_id", "account_type"])

    # 3. Cashflow (Categories, Recurring Rules, Cash Transactions, Occurrences)
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("icon", sa.String(length=64), nullable=True),
        sa.Column("color_hex", sa.String(length=7), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["categories.id"],
            name="fk_categories_parent_id_categories",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_categories_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_categories"),
        sa.UniqueConstraint(
            "user_id",
            "parent_id",
            "name",
            "kind",
            name="uq_categories_user_scope",
        ),
    )
    op.create_index("ix_categories_user_kind", "categories", ["user_id", "kind"])

    op.create_table(
        "recurring_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("rule_type", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("is_variable_amount", sa.Boolean(), nullable=False),
        sa.Column("is_extraordinary", sa.Boolean(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("frequency", sa.String(length=20), nullable=False),
        sa.Column("interval_count", sa.SmallInteger(), nullable=False),
        sa.Column("day_of_month", sa.SmallInteger(), nullable=True),
        sa.Column("month_of_year", sa.SmallInteger(), nullable=True),
        sa.Column("day_of_week", sa.SmallInteger(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("next_run_date", sa.Date(), nullable=True),
        sa.Column("execution_mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount > 0", name="ck_recurring_rules_amount_positive"),
        sa.CheckConstraint("interval_count >= 1", name="ck_recurring_rules_interval_count_positive"),
        sa.CheckConstraint(
            "day_of_month IS NULL OR (day_of_month >= 1 AND day_of_month <= 31)",
            name="ck_recurring_rules_day_of_month_range",
        ),
        sa.CheckConstraint(
            "month_of_year IS NULL OR (month_of_year >= 1 AND month_of_year <= 12)",
            name="ck_recurring_rules_month_of_year_range",
        ),
        sa.CheckConstraint(
            "day_of_week IS NULL OR (day_of_week >= 0 AND day_of_week <= 6)",
            name="ck_recurring_rules_day_of_week_range",
        ),
        sa.CheckConstraint(
            "(rule_type != 'TRANSFER') OR (target_account_id IS NOT NULL AND target_account_id != account_id)",
            name="ck_recurring_rules_transfer_requires_distinct_target",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_recurring_rules_account_id_accounts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_recurring_rules_category_id_categories",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_account_id"],
            ["accounts.id"],
            name="fk_recurring_rules_target_account_id_accounts",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_recurring_rules_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_recurring_rules"),
    )
    op.create_index(
        "ix_recurring_rules_user_status_next",
        "recurring_rules",
        ["user_id", "status", "next_run_date"],
    )

    op.create_table(
        "cash_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recurring_rule_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("transaction_type", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_extraordinary", sa.Boolean(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("counterparty", sa.String(length=160), nullable=True),
        sa.Column("transfer_group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String(length=40)), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(transaction_type IN ('INCOME', 'TRANSFER_IN') AND amount > 0) "
            "OR (transaction_type IN ('EXPENSE', 'TRANSFER_OUT') AND amount < 0) "
            "OR (transaction_type = 'INVESTMENT_SETTLEMENT' AND amount != 0)",
            name="ck_cash_transactions_amount_sign_matches_type",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_cash_transactions_account_id_accounts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_cash_transactions_category_id_categories",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["recurring_rule_id"],
            ["recurring_rules.id"],
            name="fk_cash_transactions_recurring_rule_id_recurring_rules",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_cash_transactions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_cash_transactions"),
    )
    op.create_index(
        "ix_cash_transactions_user_occurred",
        "cash_transactions",
        ["user_id", "occurred_at"],
    )
    op.create_index(
        "ix_cash_transactions_account_occurred",
        "cash_transactions",
        ["account_id", "occurred_at"],
    )
    op.create_index(
        "ix_cash_transactions_transfer_group",
        "cash_transactions",
        ["transfer_group_id"],
    )

    op.create_table(
        "recurring_occurrences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recurring_rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("expected_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("cash_transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["cash_transaction_id"],
            ["cash_transactions.id"],
            name="fk_recurring_occurrences_cash_transaction_id_cash_transactions",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["recurring_rule_id"],
            ["recurring_rules.id"],
            name="fk_recurring_occurrences_recurring_rule_id_recurring_rules",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_recurring_occurrences"),
        sa.UniqueConstraint(
            "recurring_rule_id",
            "scheduled_date",
            name="uq_recurring_occurrences_rule_date",
        ),
    )
    op.create_index(
        "ix_recurring_occurrences_status_date",
        "recurring_occurrences",
        ["status", "scheduled_date"],
    )

    # 4. Portfolio, Instruments, Bonds & PAC
    op.create_table(
        "instruments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("isin", sa.String(length=12), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("asset_class", sa.String(length=24), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("exchange_mic", sa.String(length=12), nullable=True),
        sa.Column("sector", sa.String(length=80), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_instruments"),
    )
    op.create_index("ix_instruments_isin", "instruments", ["isin"], unique=True)
    op.create_index("ix_instruments_asset_class_name", "instruments", ["asset_class", "name"])

    op.create_table(
        "instrument_provider_symbols",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=24), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["instruments.id"],
            name="fk_instrument_provider_symbols_instrument_id_instruments",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_instrument_provider_symbols"),
        sa.UniqueConstraint(
            "instrument_id",
            "provider",
            "symbol",
            name="uq_instrument_provider_symbol",
        ),
    )
    op.create_index(
        "ix_provider_symbol_lookup",
        "instrument_provider_symbols",
        ["provider", "symbol"],
    )

    op.create_table(
        "bond_details",
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issuer", sa.String(length=160), nullable=False),
        sa.Column("face_value", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("coupon_rate", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("coupon_frequency", sa.String(length=20), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("maturity_date", sa.Date(), nullable=False),
        sa.Column("day_count_convention", sa.String(length=16), nullable=False),
        sa.Column("withholding_tax_rate", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("face_value > 0", name="ck_bond_details_face_value_positive"),
        sa.CheckConstraint("coupon_rate >= 0", name="ck_bond_details_coupon_rate_non_negative"),
        sa.CheckConstraint(
            "withholding_tax_rate >= 0 AND withholding_tax_rate <= 1",
            name="ck_bond_details_tax_range",
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["instruments.id"],
            name="fk_bond_details_instrument_id_instruments",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("instrument_id", name="pk_bond_details"),
    )

    op.create_table(
        "pac_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("funding_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("frequency", sa.String(length=20), nullable=False),
        sa.Column("day_of_month", sa.SmallInteger(), nullable=True),
        sa.Column("day_of_week", sa.SmallInteger(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("next_run_date", sa.Date(), nullable=True),
        sa.Column("execution_mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount > 0", name="ck_pac_plans_amount_positive"),
        sa.CheckConstraint(
            "day_of_month IS NULL OR (day_of_month >= 1 AND day_of_month <= 31)",
            name="ck_pac_plans_day_of_month_range",
        ),
        sa.CheckConstraint(
            "day_of_week IS NULL OR (day_of_week >= 0 AND day_of_week <= 6)",
            name="ck_pac_plans_day_of_week_range",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_pac_plans_account_id_accounts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["funding_account_id"],
            ["accounts.id"],
            name="fk_pac_plans_funding_account_id_accounts",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["instruments.id"],
            name="fk_pac_plans_instrument_id_instruments",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_pac_plans_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_pac_plans"),
    )
    op.create_index("ix_pac_plans_user_status_next", "pac_plans", ["user_id", "status", "next_run_date"])

    op.create_table(
        "portfolio_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pac_plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("linked_cash_transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("transaction_type", sa.String(length=24), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("gross_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("fees", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("taxes", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("accrued_interest", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("fx_rate_to_base", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("quantity >= 0", name="ck_portfolio_transactions_quantity_non_negative"),
        sa.CheckConstraint("unit_price >= 0", name="ck_portfolio_transactions_unit_price_non_negative"),
        sa.CheckConstraint("fees >= 0", name="ck_portfolio_transactions_fees_non_negative"),
        sa.CheckConstraint("taxes >= 0", name="ck_portfolio_transactions_taxes_non_negative"),
        sa.CheckConstraint("fx_rate_to_base > 0", name="ck_portfolio_transactions_fx_rate_positive"),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_portfolio_transactions_account_id_accounts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["instruments.id"],
            name="fk_portfolio_transactions_instrument_id_instruments",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["linked_cash_transaction_id"],
            ["cash_transactions.id"],
            name="fk_portfolio_transactions_linked_cash_transaction_id_cash_transactions",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["pac_plan_id"],
            ["pac_plans.id"],
            name="fk_portfolio_transactions_pac_plan_id_pac_plans",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_portfolio_transactions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_portfolio_transactions"),
    )
    op.create_index(
        "ix_portfolio_tx_user_executed",
        "portfolio_transactions",
        ["user_id", "executed_at"],
    )
    op.create_index(
        "ix_portfolio_tx_account_instrument",
        "portfolio_transactions",
        ["account_id", "instrument_id", "executed_at"],
    )

    op.create_table(
        "pac_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pac_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("portfolio_transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["pac_plan_id"],
            ["pac_plans.id"],
            name="fk_pac_executions_pac_plan_id_pac_plans",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_transaction_id"],
            ["portfolio_transactions.id"],
            name="fk_pac_executions_portfolio_transaction_id_portfolio_transactions",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_pac_executions"),
        sa.UniqueConstraint("pac_plan_id", "scheduled_date", name="uq_pac_executions_plan_date"),
    )
    op.create_index("ix_pac_executions_status_date", "pac_executions", ["status", "scheduled_date"])

    # 5. Market Data & Analytics (TimescaleDB Hypertables)
    op.create_table(
        "market_prices",
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("interval", sa.String(length=12), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("high", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("low", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("close", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("source", sa.String(length=24), nullable=False),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["instruments.id"],
            name="fk_market_prices_instrument_id_instruments",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("instrument_id", "interval", "recorded_at", name="pk_market_prices"),
    )
    op.execute(
        "SELECT create_hypertable('market_prices', 'recorded_at', if_not_exists => TRUE);"
    )

    op.create_table(
        "fx_rates",
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("quote_currency", sa.String(length=3), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rate", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("base_currency", "quote_currency", "recorded_at", name="pk_fx_rates"),
    )
    op.execute("SELECT create_hypertable('fx_rates', 'recorded_at', if_not_exists => TRUE);")

    op.create_table(
        "portfolio_daily_snapshots",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("cash_value_base", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("invested_cost_base", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("market_value_base", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("unrealized_pnl_base", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("realized_pnl_base", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_portfolio_daily_snapshots_account_id_accounts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_portfolio_daily_snapshots_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "user_id",
            "account_id",
            "snapshot_date",
            name="pk_portfolio_daily_snapshots",
        ),
    )
    op.execute(
        "SELECT create_hypertable('portfolio_daily_snapshots', 'snapshot_date', if_not_exists => TRUE);"
    )


def downgrade() -> None:
    op.drop_table("portfolio_daily_snapshots")
    op.drop_table("fx_rates")
    op.drop_table("market_prices")
    op.drop_table("pac_executions")
    op.drop_table("portfolio_transactions")
    op.drop_table("pac_plans")
    op.drop_table("bond_details")
    op.drop_table("instrument_provider_symbols")
    op.drop_table("instruments")
    op.drop_table("recurring_occurrences")
    op.drop_table("cash_transactions")
    op.drop_table("recurring_rules")
    op.drop_table("categories")
    op.drop_table("accounts")
    op.drop_table("institutions")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
