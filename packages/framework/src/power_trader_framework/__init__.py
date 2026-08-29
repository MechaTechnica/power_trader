"""
Power Framework

Pure protocols and types for building trading applications.
NO IMPLEMENTATIONS - only interfaces and data structures.
"""

__version__ = "0.1.0"

from power_trader_framework.types.market import (MarketBar, TickerSymbol,
                                                 TimeInterval)
from power_trader_framework.types.signals import (SignalMetadata, SignalType,
                                                  TradingSignal)

__all__ = [
    "SignalType",
    "MarketBar",
    "TickerSymbol",
    "TimeInterval",
    "SignalMetadata",
    "TradingSignal",
]
