from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import (
    AssetQuantity,
    Base,
    CouponRateValue,
    FxRateValue,
    MoneyAmount,
    TaxRateValue,
    TimestampMixin,
    UnitPrice,
    UUIDPrimaryKeyMixin,
)
from app.modules.cashflow.models import (
    ExecutionMode,
    OccurrenceStatus,
    RecurrenceFrequency,
    RuleStatus,
)


class AssetClass(StrEnum):
    STOCK = "STOCK"
    ETF = "ETF"
    BOND = "BOND"
    MUTUAL_FUND = "MUTUAL_FUND"
    ETC = "ETC"


class MarketDataProvider(StrEnum):
    YAHOO = "YAHOO"
    FINNHUB = "FINNHUB"
    TWELVE_DATA = "TWELVE_DATA"
    MANUAL = "MANUAL"


class CouponFrequency(StrEnum):
    ANNUAL = "ANNUAL"
    SEMI_ANNUAL = "SEMI_ANNUAL"
    QUARTERLY = "QUARTERLY"
    ZERO_COUPON = "ZERO_COUPON"


class DayCountConvention(StrEnum):
    ACT_ACT = "ACT_ACT"
    THIRTY_360 = "30_360"
    ACT_365 = "ACT_365"


class PortfolioTransactionType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    COUPON = "COUPON"
    FEE = "FEE"
    TAX = "TAX"
    SPLIT = "SPLIT"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"


class Instrument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "instruments"
    __table_args__ = (Index("ix_instruments_asset_class_name", "asset_class", "name"),)

    isin: Mapped[str | None] = mapped_column(String(12), unique=True, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_class: Mapped[AssetClass] = mapped_column(
        SAEnum(AssetClass, native_enum=False, length=24, validate_strings=True),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    exchange_mic: Mapped[str | None] = mapped_column(String(12), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(80), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    provider_symbols: Mapped[list["InstrumentProviderSymbol"]] = relationship(
        back_populates="instrument",
        cascade="all, delete-orphan",
    )
    bond_detail: Mapped["BondDetail | None"] = relationship(
        back_populates="instrument",
        cascade="all, delete-orphan",
        uselist=False,
    )


class InstrumentProviderSymbol(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "instrument_provider_symbols"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id",
            "provider",
            "symbol",
            name="uq_instrument_provider_symbol",
        ),
        Index("ix_provider_symbol_lookup", "provider", "symbol"),
    )

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("instruments.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[MarketDataProvider] = mapped_column(
        SAEnum(MarketDataProvider, native_enum=False, length=24, validate_strings=True),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    instrument: Mapped[Instrument] = relationship(back_populates="provider_symbols")


class BondDetail(TimestampMixin, Base):
    __tablename__ = "bond_details"
    __table_args__ = (
        CheckConstraint("face_value > 0", name="face_value_positive"),
        CheckConstraint("coupon_rate >= 0", name="coupon_rate_non_negative"),
        CheckConstraint("withholding_tax_rate >= 0 AND withholding_tax_rate <= 1", name="tax_range"),
    )

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("instruments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    issuer: Mapped[str] = mapped_column(String(160), nullable=False)
    face_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 4, asdecimal=True),
        nullable=False,
        default=Decimal("100.0000"),
    )
    coupon_rate: Mapped[Decimal] = mapped_column(
        CouponRateValue,
        nullable=False,
        default=Decimal("0.000000"),
    )
    coupon_frequency: Mapped[CouponFrequency] = mapped_column(
        SAEnum(CouponFrequency, native_enum=False, length=20, validate_strings=True),
        nullable=False,
        default=CouponFrequency.SEMI_ANNUAL,
    )
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    maturity_date: Mapped[date] = mapped_column(Date, nullable=False)
    day_count_convention: Mapped[DayCountConvention] = mapped_column(
        SAEnum(DayCountConvention, native_enum=False, length=16, validate_strings=True),
        nullable=False,
        default=DayCountConvention.ACT_ACT,
    )
    withholding_tax_rate: Mapped[Decimal] = mapped_column(
        TaxRateValue,
        nullable=False,
        default=Decimal("0.1250"),
    )

    instrument: Mapped[Instrument] = relationship(back_populates="bond_detail")


class PacPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "pac_plans"
    __table_args__ = (
        Index("ix_pac_plans_user_status_next", "user_id", "status", "next_run_date"),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint(
            "day_of_month IS NULL OR (day_of_month >= 1 AND day_of_month <= 31)",
            name="day_of_month_range",
        ),
        CheckConstraint(
            "day_of_week IS NULL OR (day_of_week >= 0 AND day_of_week <= 6)",
            name="day_of_week_range",
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
    funding_account_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("instruments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(MoneyAmount, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    frequency: Mapped[RecurrenceFrequency] = mapped_column(
        SAEnum(RecurrenceFrequency, native_enum=False, length=20, validate_strings=True),
        nullable=False,
        default=RecurrenceFrequency.MONTHLY,
    )
    day_of_month: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
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

    executions: Mapped[list["PacExecution"]] = relationship(
        back_populates="pac_plan",
        cascade="all, delete-orphan",
    )


class PortfolioTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "portfolio_transactions"
    __table_args__ = (
        Index("ix_portfolio_tx_user_executed", "user_id", "executed_at"),
        Index("ix_portfolio_tx_account_instrument", "account_id", "instrument_id", "executed_at"),
        CheckConstraint("quantity >= 0", name="quantity_non_negative"),
        CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
        CheckConstraint("fees >= 0", name="fees_non_negative"),
        CheckConstraint("taxes >= 0", name="taxes_non_negative"),
        CheckConstraint("fx_rate_to_base > 0", name="fx_rate_positive"),
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
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("instruments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    pac_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pac_plans.id", ondelete="SET NULL"),
        nullable=True,
    )
    linked_cash_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cash_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    transaction_type: Mapped[PortfolioTransactionType] = mapped_column(
        SAEnum(PortfolioTransactionType, native_enum=False, length=24, validate_strings=True),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(
        AssetQuantity,
        nullable=False,
        default=Decimal("0"),
    )
    unit_price: Mapped[Decimal] = mapped_column(
        UnitPrice,
        nullable=False,
        default=Decimal("0"),
    )
    gross_amount: Mapped[Decimal] = mapped_column(MoneyAmount, nullable=False)
    fees: Mapped[Decimal] = mapped_column(MoneyAmount, nullable=False, default=Decimal("0.00"))
    taxes: Mapped[Decimal] = mapped_column(MoneyAmount, nullable=False, default=Decimal("0.00"))
    accrued_interest: Mapped[Decimal] = mapped_column(
        MoneyAmount,
        nullable=False,
        default=Decimal("0.00"),
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    fx_rate_to_base: Mapped[Decimal] = mapped_column(
        FxRateValue,
        nullable=False,
        default=Decimal("1.00000000"),
    )
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PacExecution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "pac_executions"
    __table_args__ = (
        UniqueConstraint("pac_plan_id", "scheduled_date", name="uq_pac_executions_plan_date"),
        Index("ix_pac_executions_status_date", "status", "scheduled_date"),
    )

    pac_plan_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pac_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[OccurrenceStatus] = mapped_column(
        SAEnum(OccurrenceStatus, native_enum=False, length=16, validate_strings=True),
        nullable=False,
        default=OccurrenceStatus.PENDING,
    )
    portfolio_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("portfolio_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pac_plan: Mapped[PacPlan] = relationship(back_populates="executions")
