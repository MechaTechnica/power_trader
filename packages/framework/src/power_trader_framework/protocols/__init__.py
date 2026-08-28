"""Protocol definitions for the Power Trader framework."""

from power_trader_framework.protocols.config import IConfigProvider
from power_trader_framework.protocols.data import IMarketDataProvider, IMarketScanner
from power_trader_framework.protocols.lifecycle import IApplicationLifecycle, IHealthCheck
from power_trader_framework.protocols.output import IOutputPresenter
from power_trader_framework.protocols.strategy import ISignalAggregator, IStrategy

__all__ = [
    "IConfigProvider",
    "IMarketDataProvider",
    "IMarketScanner",
    "IApplicationLifecycle",
    "IHealthCheck",
    "IOutputPresenter",
    "ISignalAggregator",
    "IStrategy",
]
