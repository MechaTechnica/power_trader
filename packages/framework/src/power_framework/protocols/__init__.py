"""Protocol definitions for the Power Trader framework."""

from power_framework.protocols.config import ConfigProvider
from power_framework.protocols.container import Container
from power_framework.protocols.data import MarketDataProvider, MarketScanner
from power_framework.protocols.lifecycle import ApplicationLifecycle, HealthCheck
from power_framework.protocols.output import OutputPresenter
from power_framework.protocols.strategy import SignalAggregator, Strategy

__all__ = [
                                                   "ApplicationLifecycle",
                                                   "ConfigProvider",
                                                   "Container",
                                                   "HealthCheck",
                                                   "MarketDataProvider",
                                                   "MarketScanner",
                                                   "OutputPresenter",
                                                   "SignalAggregator",
                                                   "Strategy",
]
