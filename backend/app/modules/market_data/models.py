import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, FxRateValue, UnitPrice
from app.modules.portfolio.models import MarketDataProvider


class PriceInterval(StrEnum):
    SPOT = "SPOT"
    M15 = "15M"
    D1 = "1D"


class MarketPrice(Base):
    """TimescaleDB hypertable partitioned by recorded_at."""

    __tablename__ = "market_prices"

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("instruments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    interval: Mapped[PriceInterval] = mapped_column(
        SAEnum(PriceInterval, native_enum=False, length=12, validate_strings=True),
        primary_key=True,
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    open: Mapped[Decimal | None] = mapped_column(UnitPrice, nullable=True)
    high: Mapped[Decimal | None] = mapped_column(UnitPrice, nullable=True)
    low: Mapped[Decimal | None] = mapped_column(UnitPrice, nullable=True)
    close: Mapped[Decimal] = mapped_column(UnitPrice, nullable=False)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    source: Mapped[MarketDataProvider] = mapped_column(
        SAEnum(MarketDataProvider, native_enum=False, length=24, validate_strings=True),
        nullable=False,
    )


class FxRate(Base):
    """TimescaleDB hypertable partitioned by recorded_at."""

    __tablename__ = "fx_rates"

    base_currency: Mapped[str] = mapped_column(String(3), primary_key=True)
    quote_currency: Mapped[str] = mapped_column(String(3), primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    rate: Mapped[Decimal] = mapped_column(FxRateValue, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="FRANKFURTER_ECB")
