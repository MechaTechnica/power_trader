"""
Power Framework

Protocols, types, and application abstractions for building trading
applications. Contains interfaces and data structures - concrete runtime
implementations live in ``power-core``.
"""

__version__ = "0.1.0"

from power_trader_framework.application import (ApplicationBase, IApplication,
                                                create_application)
from power_trader_framework.protocols.container import IContainer
from power_trader_framework.protocols.plugin import IPluginRegistry
from power_trader_framework.settings import FrameworkSettings
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
    "ApplicationBase",
    "IApplication",
    "IContainer",
    "IPluginRegistry",
    "FrameworkSettings",
    "create_application",
]
