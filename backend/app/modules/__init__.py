"""Import all ORM models here so SQLAlchemy Base.metadata is always fully registered."""

from app.modules.accounts.models import Account, Institution
from app.modules.analytics.models import PortfolioDailySnapshot
from app.modules.cashflow.models import (
    CashTransaction,
    Category,
    RecurringOccurrence,
    RecurringRule,
)
from app.modules.identity.models import RefreshToken, User
from app.modules.market_data.models import FxRate, MarketPrice
from app.modules.portfolio.models import (
    BondDetail,
    Instrument,
    InstrumentProviderSymbol,
    PacExecution,
    PacPlan,
    PortfolioTransaction,
)

__all__ = [
    "Account",
    "BondDetail",
    "CashTransaction",
    "Category",
    "FxRate",
    "Institution",
    "Instrument",
    "InstrumentProviderSymbol",
    "MarketPrice",
    "PacExecution",
    "PacPlan",
    "PortfolioDailySnapshot",
    "PortfolioTransaction",
    "RecurringOccurrence",
    "RecurringRule",
    "RefreshToken",
    "User",
]
