"""Tests for the trading app dependency container wiring."""

from power_day_trader.adapters.primary.cli_adapter import CLIAdapter
from power_day_trader.main import PowerDayTraderApplication
from power_trader_framework.protocols.container import IContainer
from power_trader_framework.protocols.data import IMarketDataProvider
from power_trader_framework.protocols.strategy import ISignalAggregator


def _build_container() -> IContainer:
    """Build a container the same way the framework does, without running lifecycle hooks."""
    app = PowerDayTraderApplication()
    app.build()
    return app.container


def test_build_container_resolves_cli_adapter():
    container = _build_container()
    cli_adapter = container.resolve(CLIAdapter)
    assert isinstance(cli_adapter, CLIAdapter)


def test_build_container_resolves_singletons():
    container = _build_container()
    aggregator = container.resolve(ISignalAggregator)
    assert container.resolve(ISignalAggregator) is aggregator


def test_build_container_provides_market_data():
    container = _build_container()
    provider = container.resolve(IMarketDataProvider)
    # The IB adapter is configured with defaults (no connection established during resolve).
    assert provider is not None
