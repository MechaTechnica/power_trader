"""Power Day Trader application plugin."""

from power_day_trader.adapters.primary.cli_adapter import CLIAdapter
from power_day_trader.adapters.secondary.ib_provider import \
    InteractiveBrokersAdapter
from power_day_trader.adapters.secondary.signal_aggregator import \
    WeightedAverageAggregator
from power_day_trader.adapters.secondary.terminal_output import \
    TerminalOutputAdapter
from power_day_trader.config.settings import PowerTraderSettings
from power_day_trader.core.strategy_registry import StrategyRegistry
from power_day_trader.core.use_cases.monitor_stocks import MonitorStocksUseCase
from power_framework.plugins import Plugin
from power_framework.protocols.container import Container
from power_framework.protocols.lifecycle import LifecycleRegistry
from power_framework.protocols.output import OutputPresenter
from power_market.protocols.data import MarketDataProvider
from power_market.protocols.output import SignalPresenter
from power_market.protocols.strategy import SignalAggregator


class PowerDayTraderPlugin(Plugin):
    """Power Day Trader application wiring."""

    def register(self, container: Container, runtime: LifecycleRegistry) -> None:
        """Register the application's settings, adapters, and use cases."""
        app_settings: PowerTraderSettings = PowerTraderSettings.load()
        container.register_instance(PowerTraderSettings, app_settings)
        container.register(OutputPresenter, TerminalOutputAdapter)
        container.register(SignalPresenter, TerminalOutputAdapter)

        container.register(
            MarketDataProvider,
            InteractiveBrokersAdapter,
            host=app_settings.ib.host,
            port=app_settings.ib.port,
            client_id=app_settings.ib.client_id,
        )
        container.register(SignalAggregator, WeightedAverageAggregator)
        container.register(StrategyRegistry, StrategyRegistry)
        container.register(MonitorStocksUseCase, MonitorStocksUseCase)
        container.register(CLIAdapter, CLIAdapter)

        # Lifecycle ordering: infrastructure first, then domain services.
        runtime.register(MarketDataProvider)
        runtime.register(StrategyRegistry)
