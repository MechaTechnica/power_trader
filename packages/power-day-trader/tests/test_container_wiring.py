"""Tests for the trading app dependency container wiring."""

from power_core.container import Container
from power_day_trader.adapters.primary.cli_adapter import CLIAdapter
from power_day_trader.plugin import PowerDayTraderPlugin
from power_framework.application import Runtime
from power_market.protocols.data import MarketDataProvider
from power_market.protocols.strategy import SignalAggregator


def _build_container() -> Container:
    """Build a container the same way the framework does, without running the CLI."""
    container = Container()
    PowerDayTraderPlugin().register(container, Runtime(container))
    return container


def test_build_container_resolves_cli_adapter():
    container = _build_container()
    cli_adapter = container.resolve(CLIAdapter)
    assert isinstance(cli_adapter, CLIAdapter)


def test_build_container_resolves_singletons():
    container = _build_container()
    aggregator = container.resolve(SignalAggregator)
    assert container.resolve(SignalAggregator) is aggregator


def test_build_container_provides_market_data():
    container = _build_container()
    provider = container.resolve(MarketDataProvider)
    # The IB adapter is configured with defaults (no connection established during resolve).
    assert provider is not None
