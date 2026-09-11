"""Protocol definitions for the Power Trader framework."""

from power_trader_framework.protocols.config import ConfigProvider
from power_trader_framework.protocols.container import Container
from power_trader_framework.protocols.data import (MarketDataProvider,
                                                   MarketScanner)
from power_trader_framework.protocols.lifecycle import (ApplicationLifecycle,
                                                        HealthCheck)
from power_trader_framework.protocols.output import OutputPresenter
from power_trader_framework.protocols.plugin import PluginRegistry
from power_trader_framework.protocols.strategy import (SignalAggregator,
                                                       Strategy)

__all__ = [
    "ConfigProvider",
    "Container",
    "MarketDataProvider",
    "MarketScanner",
    "ApplicationLifecycle",
    "HealthCheck",
    "OutputPresenter",
    "PluginRegistry",
    "SignalAggregator",
    "Strategy",
]
