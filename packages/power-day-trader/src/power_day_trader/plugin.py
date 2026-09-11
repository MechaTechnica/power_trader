"""Power Day Trader application plugin."""

from power_day_trader.adapters.primary.cli_adapter import CLIAdapter
from power_day_trader.adapters.secondary.ib_provider import \
    InteractiveBrokersAdapter
from power_day_trader.adapters.secondary.signal_aggregator import \
    WeightedAverageAggregator
from power_day_trader.adapters.secondary.terminal_output import \
    TerminalOutputAdapter
from power_day_trader.config.settings import PowerTraderSettings
from power_day_trader.core.use_cases.monitor_stocks import MonitorStocksUseCase
from power_trader_framework.plugins import Plugin
from power_trader_framework.protocols.container import Container
from power_trader_framework.protocols.data import MarketDataProvider
from power_trader_framework.protocols.output import OutputPresenter
from power_trader_framework.protocols.strategy import SignalAggregator


class PowerDayTraderPlugin(Plugin):
    """Power Day Trader application wiring."""

    def on_register(self, container: Container) -> None:
        """Register the application's settings, adapters, and use cases."""
        app_settings = PowerTraderSettings.load()
        container.register_instance(PowerTraderSettings, app_settings)
        container.register(OutputPresenter, TerminalOutputAdapter)

        container.register(
            MarketDataProvider,
            InteractiveBrokersAdapter,
            host=app_settings.ib.host,
            port=app_settings.ib.port,
            client_id=app_settings.ib.client_id,
        )
        container.register(SignalAggregator, WeightedAverageAggregator)
        container.register(MonitorStocksUseCase, MonitorStocksUseCase)
        container.register(CLIAdapter, CLIAdapter)
