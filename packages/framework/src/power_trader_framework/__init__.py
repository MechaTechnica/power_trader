"""
Power Framework

Protocols, types, and application abstractions for building trading
applications. Contains interfaces and data structures - concrete runtime
implementations live in ``power-core``.
"""

__version__ = "0.1.0"

from power_trader_framework.application import (Application, ApplicationBase,
                                                ApplicationBuilder,
                                                ApplicationRuntime)
from power_trader_framework.plugins import Plugin
from power_trader_framework.protocols.container import Container
from power_trader_framework.settings import FrameworkSettings, JsonFileSettings
from power_trader_framework.types.market import (MarketBar, TickerSymbol,
                                                 TimeInterval)
from power_trader_framework.types.signals import (SignalMetadata, SignalType,
                                                  TradingSignal)

__all__ = [
                                                "Application",
                                                "ApplicationBase",
                                                "ApplicationBuilder",
                                                "ApplicationRuntime",
                                                "Container",
                                                "FrameworkSettings",
                                                "JsonFileSettings",
                                                "MarketBar",
                                                "Plugin",
                                                "SignalMetadata",
                                                "SignalType",
                                                "TickerSymbol",
                                                "TimeInterval",
                                                "TradingSignal",
]
