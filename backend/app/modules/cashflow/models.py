import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, MoneyAmount, TimestampMixin, UUIDPrimaryKeyMixin


class CategoryKind(StrEnum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class CashTransactionType(StrEnum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    INVESTMENT_SETTLEMENT = "INVESTMENT_SETTLEMENT"


class RecurringRuleType(StrEnum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"


class RecurrenceFrequency(StrEnum):
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    SEMI_ANNUAL = "SEMI_ANNUAL"
    YEARLY = "YEARLY"


class ExecutionMode(StrEnum):
    AUTO_DRAFT = "AUTO_DRAFT"
    AUTO_EXECUTE = "AUTO_EXECUTE"


class RuleStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class OccurrenceStatus(StrEnum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    SKIPPED = "SKIPPED"


class Category(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (
        Index("ix_categories_user_kind", "user_id", "kind"),
        UniqueConstraint("user_id", "parent_id", "name", "kind", name="uq_categories_user_scope"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    kind: Mapped[CategoryKind] = mapped_column(
        SAEnum(CategoryKind, native_enum=False, length=16, validate_strings=True),
        nullable=False,
    )
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    color_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class RecurringRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recurring_rules"
    __table_args__ = (
        Index("ix_recurring_rules_user_status_next", "user_id", "status", "next_run_date"),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("interval_count >= 1", name="interval_count_positive"),
        CheckConstraint(
            "day_of_month IS NULL OR (day_of_month >= 1 AND day_of_month <= 31)",
            name="day_of_month_range",
        ),
        CheckConstraint(
            "month_of_year IS NULL OR (month_of_year >= 1 AND month_of_year <= 12)",
            name="month_of_year_range",
        ),
        CheckConstraint(
            "day_of_week IS NULL OR (day_of_week >= 0 AND day_of_week <= 6)",
            name="day_of_week_range",
        ),
        CheckConstraint(
            "(rule_type != 'TRANSFER') "
            "OR (target_account_id IS NOT NULL AND target_account_id != account_id)",
            name="transfer_requires_distinct_target",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_account_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    rule_type: Mapped[RecurringRuleType] = mapped_column(
        SAEnum(RecurringRuleType, native_enum=False, length=16, validate_strings=True),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(MoneyAmount, nullable=False)
    is_variable_amount: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_extraordinary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    frequency: Mapped[RecurrenceFrequency] = mapped_column(
        SAEnum(RecurrenceFrequency, native_enum=False, length=20, validate_strings=True),
        nullable=False,
    )
    interval_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    day_of_month: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    month_of_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    day_of_week: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_run_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    execution_mode: Mapped[ExecutionMode] = mapped_column(
        SAEnum(ExecutionMode, native_enum=False, length=20, validate_strings=True),
        nullable=False,
        default=ExecutionMode.AUTO_DRAFT,
    )
    status: Mapped[RuleStatus] = mapped_column(
        SAEnum(RuleStatus, native_enum=False, length=16, validate_strings=True),
        nullable=False,
        default=RuleStatus.ACTIVE,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    occurrences: Mapped[list["RecurringOccurrence"]] = relationship(
        back_populates="recurring_rule",
        cascade="all, delete-orphan",
    )


class CashTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cash_transactions"
    __table_args__ = (
        Index("ix_cash_transactions_user_occurred", "user_id", "occurred_at"),
        Index("ix_cash_transactions_account_occurred", "account_id", "occurred_at"),
        Index("ix_cash_transactions_transfer_group", "transfer_group_id"),
        CheckConstraint(
            "(transaction_type IN ('INCOME', 'TRANSFER_IN') AND amount > 0) "
            "OR (transaction_type IN ('EXPENSE', 'TRANSFER_OUT') AND amount < 0) "
            "OR (transaction_type = 'INVESTMENT_SETTLEMENT' AND amount != 0)",
            name="amount_sign_matches_type",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    recurring_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("recurring_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
    transaction_type: Mapped[CashTransactionType] = mapped_column(
        SAEnum(CashTransactionType, native_enum=False, length=32, validate_strings=True),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(MoneyAmount, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_extraordinary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    counterparty: Mapped[str | None] = mapped_column(String(160), nullable=True)
    transfer_group_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String(40)), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class RecurringOccurrence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recurring_occurrences"
    __table_args__ = (
        UniqueConstraint(
            "recurring_rule_id",
            "scheduled_date",
            name="uq_recurring_occurrences_rule_date",
        ),
        Index("ix_recurring_occurrences_status_date", "status", "scheduled_date"),
    )

    recurring_rule_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("recurring_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_amount: Mapped[Decimal] = mapped_column(MoneyAmount, nullable=False)
    status: Mapped[OccurrenceStatus] = mapped_column(
        SAEnum(OccurrenceStatus, native_enum=False, length=16, validate_strings=True),
        nullable=False,
        default=OccurrenceStatus.PENDING,
    )
    cash_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cash_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    recurring_rule: Mapped[RecurringRule] = relationship(back_populates="occurrences")
