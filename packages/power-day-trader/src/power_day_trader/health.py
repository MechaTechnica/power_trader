"""Readiness checks for Power Day Trader.

Each check implements the framework's :class:`HealthCheck` protocol and is
registered with the runtime's :class:`HealthCheckRegistry`, so ``/ready``
reports the same standard shape as every other framework application.
"""

from power_day_trader.adapters.secondary.ib_provider import InteractiveBrokersAdapter
from power_day_trader.core.strategy_registry import StrategyRegistry
from power_framework.health import HealthStatus
from power_market.protocols.data import MarketDataProvider


class IBConnectionCheck:
    """Report whether the Interactive Brokers connection is established."""

    name = "ib_connection"

    def __init__(self, adapter: InteractiveBrokersAdapter) -> None:
        self._adapter = adapter

    async def check(self) -> HealthStatus:
        if self._adapter.connected:
            return HealthStatus.healthy(self.name, "connected to IB")
        return HealthStatus.unhealthy(self.name, "not connected to IB")


class MarketDataCheck:
    """Report whether a market-data provider is wired and usable."""

    name = "market_data"

    def __init__(self, provider: MarketDataProvider) -> None:
        self._provider = provider

    async def check(self) -> HealthStatus:
        # The provider is present and constructed; connectivity is reported by
        # IBConnectionCheck, so this confirms the dependency is wired.
        if self._provider is not None:
            return HealthStatus.healthy(self.name)
        return HealthStatus.unhealthy(self.name, "no market data provider")


class StrategiesLoadedCheck:
    """Report whether at least one strategy has been registered."""

    name = "strategies_loaded"

    def __init__(self, registry: StrategyRegistry) -> None:
        self._registry = registry

    async def check(self) -> HealthStatus:
        count = len(self._registry.strategies)
        if count > 0:
            return HealthStatus.healthy(self.name, f"{count} strategies loaded")
        return HealthStatus.unhealthy(self.name, "no strategies loaded")
