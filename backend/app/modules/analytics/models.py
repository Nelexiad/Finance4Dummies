import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, MoneyAmount


class PortfolioDailySnapshot(Base):
    """TimescaleDB hypertable partitioned by snapshot_date."""

    __tablename__ = "portfolio_daily_snapshots"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    cash_value_base: Mapped[Decimal] = mapped_column(
        MoneyAmount,
        nullable=False,
        default=Decimal("0.00"),
    )
    invested_cost_base: Mapped[Decimal] = mapped_column(
        MoneyAmount,
        nullable=False,
        default=Decimal("0.00"),
    )
    market_value_base: Mapped[Decimal] = mapped_column(
        MoneyAmount,
        nullable=False,
        default=Decimal("0.00"),
    )
    unrealized_pnl_base: Mapped[Decimal] = mapped_column(
        MoneyAmount,
        nullable=False,
        default=Decimal("0.00"),
    )
    realized_pnl_base: Mapped[Decimal] = mapped_column(
        MoneyAmount,
        nullable=False,
        default=Decimal("0.00"),
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
