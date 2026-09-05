"""Protocol definitions for the Power Trader framework."""

from power_trader_framework.protocols.config import IConfigProvider
from power_trader_framework.protocols.container import IContainer
from power_trader_framework.protocols.data import (IMarketDataProvider,
                                                   IMarketScanner)
from power_trader_framework.protocols.lifecycle import (IApplicationLifecycle,
                                                        IHealthCheck)
from power_trader_framework.protocols.output import IOutputPresenter
from power_trader_framework.protocols.plugin import IPluginRegistry
from power_trader_framework.protocols.strategy import (ISignalAggregator,
                                                       IStrategy)

__all__ = [
    "IConfigProvider",
    "IContainer",
    "IMarketDataProvider",
    "IMarketScanner",
    "IApplicationLifecycle",
    "IHealthCheck",
    "IOutputPresenter",
    "IPluginRegistry",
    "ISignalAggregator",
    "IStrategy",
]
