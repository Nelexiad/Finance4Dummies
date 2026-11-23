import uuid
from datetime import date
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, Date, ForeignKey, Index, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, MoneyAmount, TimestampMixin, UUIDPrimaryKeyMixin


class InstitutionType(StrEnum):
    BANK = "BANK"
    BROKER = "BROKER"
    NEOBANK = "NEOBANK"
    MIXED = "MIXED"


class AccountType(StrEnum):
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"
    BROKERAGE = "BROKERAGE"
    CASH_WALLET = "CASH_WALLET"
    DEPOSIT = "DEPOSIT"
    CREDIT_CARD = "CREDIT_CARD"


class Institution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "institutions"
    __table_args__ = (Index("ix_institutions_user_name", "user_id", "name"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    institution_type: Mapped[InstitutionType] = mapped_column(
        SAEnum(InstitutionType, native_enum=False, length=32, validate_strings=True),
        nullable=False,
        default=InstitutionType.BANK,
    )
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    color_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    logo_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    accounts: Mapped[list["Account"]] = relationship(
        back_populates="institution",
        cascade="all, delete-orphan",
    )


class Account(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "accounts"
    __table_args__ = (
        Index("ix_accounts_user_institution", "user_id", "institution_id"),
        Index("ix_accounts_user_type", "user_id", "account_type"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        SAEnum(AccountType, native_enum=False, length=32, validate_strings=True),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    initial_balance: Mapped[Decimal] = mapped_column(
        MoneyAmount,
        nullable=False,
        default=Decimal("0.00"),
    )
    initial_balance_date: Mapped[date] = mapped_column(Date, nullable=False)
    iban_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    institution: Mapped[Institution] = relationship(back_populates="accounts")
