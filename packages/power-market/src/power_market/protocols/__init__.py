"""Trading-domain protocol definitions."""

from power_market.protocols.data import MarketDataProvider, MarketScanner
from power_market.protocols.output import SignalPresenter
from power_market.protocols.strategy import SignalAggregator, Strategy

__all__ = [
    "MarketDataProvider",
    "MarketScanner",
    "SignalAggregator",
    "SignalPresenter",
    "Strategy",
]
