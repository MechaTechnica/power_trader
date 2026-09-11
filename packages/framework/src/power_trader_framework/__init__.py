"""
Power Framework

Protocols, types, and application abstractions for building trading
applications. Contains interfaces and data structures - concrete runtime
implementations live in ``power-core``.
"""

__version__ = "0.1.0"

from power_trader_framework.application import (Application, ApplicationBase,
                                                ApplicationBuilder,
                                                ApplicationRuntime,
                                                create_application)
from power_trader_framework.plugins import Plugin
from power_trader_framework.protocols.container import Container
from power_trader_framework.protocols.plugin import PluginRegistry
from power_trader_framework.settings import FrameworkSettings, JsonFileSettings
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
    "Application",
    "ApplicationBase",
    "ApplicationBuilder",
    "ApplicationRuntime",
    "Container",
    "PluginRegistry",
    "Plugin",
    "FrameworkSettings",
    "JsonFileSettings",
    "create_application",
]
