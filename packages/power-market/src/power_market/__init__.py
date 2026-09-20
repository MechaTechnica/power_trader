"""
Power Market

Trading-domain contracts: market and signal value types plus protocol
interfaces for data providers, scanners, strategies, and signal
presentation. Contains only interfaces and data structures - concrete
implementations live in application and strategy packages.
"""

__version__ = "0.1.0"

from power_market.events import (
    MarketDataReceived,
    OrderFilled,
    OrderRejected,
    OrderRequested,
    OrderSubmitted,
    SignalGenerated,
)
from power_market.protocols.data import MarketDataProvider, MarketScanner
from power_market.protocols.output import SignalPresenter
from power_market.protocols.strategy import SignalAggregator, Strategy
from power_market.types.market import MarketBar, MarketContext, TickerSymbol, TimeInterval
from power_market.types.signals import Signal, SignalIntent, SignalMetadata, SignalSource

__all__ = [
    "MarketBar",
    "MarketContext",
    "MarketDataProvider",
    "MarketDataReceived",
    "MarketScanner",
    "OrderFilled",
    "OrderRejected",
    "OrderRequested",
    "OrderSubmitted",
    "Signal",
    "SignalAggregator",
    "SignalGenerated",
    "SignalIntent",
    "SignalMetadata",
    "SignalPresenter",
    "SignalSource",
    "Strategy",
    "TickerSymbol",
    "TimeInterval",
]
