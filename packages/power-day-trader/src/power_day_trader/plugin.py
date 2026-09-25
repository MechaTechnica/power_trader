"""Power Day Trader application plugin."""

from power_day_trader.adapters.primary.cli_adapter import CLIAdapter
from power_day_trader.adapters.secondary.ib_provider import \
    InteractiveBrokersAdapter
from power_day_trader.adapters.secondary.signal_aggregator import \
    WeightedAverageAggregator
from power_day_trader.adapters.secondary.terminal_output import \
    TerminalOutputAdapter
from power_day_trader.config.settings import PowerTraderSettings
from power_day_trader.core.event_handlers import SignalToOrderHandler
from power_day_trader.core.strategy_registry import StrategyRegistry
from power_day_trader.core.use_cases.monitor_stocks import MonitorStocksUseCase
from power_day_trader.health import (IBConnectionCheck, MarketDataCheck,
                                     StrategiesLoadedCheck)
from power_framework.container import Container
from power_framework.events import EventBus
from power_framework.health import HealthCheckRegistry
from power_framework.plugins import Plugin
from power_framework.protocols.output import OutputPresenter
from power_market.events import SignalGenerated
from power_market.protocols.data import MarketDataProvider
from power_market.protocols.output import SignalPresenter
from power_market.protocols.strategy import SignalAggregator


class PowerDayTraderPlugin(Plugin):
    """Power Day Trader application wiring."""

    # Declared (not loaded) here; the framework loads it and registers it in
    # the container before ``register`` is called.
    settings_class = PowerTraderSettings

    def register(self, container: Container) -> None:
        """Register the application's adapters, use cases, and health checks."""
        app_settings: PowerTraderSettings = container.resolve(PowerTraderSettings)

        # A single shared IB adapter backs both the concrete type and the
        # ``MarketDataProvider`` interface (one connection for the whole app).
        ib_adapter = InteractiveBrokersAdapter(
            host=app_settings.ib.host,
            port=app_settings.ib.port,
            client_id=app_settings.ib.client_id,
        )

        # --- Framework ---
        container.register(OutputPresenter, TerminalOutputAdapter)

        # --- Market ---
        container.register_instance(MarketDataProvider, ib_adapter)
        container.register(SignalPresenter, TerminalOutputAdapter)
        container.register(SignalAggregator, WeightedAverageAggregator)

        # --- This project ---
        container.register_instance(InteractiveBrokersAdapter, ib_adapter)
        container.register(StrategyRegistry, StrategyRegistry)
        container.register(MonitorStocksUseCase, MonitorStocksUseCase)
        container.register(CLIAdapter, CLIAdapter)

        # Event-driven order flow: translate generated signals into the order
        # lifecycle (requested → submitted → filled/rejected) without coupling
        # the monitor use case to order execution.
        event_bus = container.resolve(EventBus)
        event_bus.subscribe(SignalGenerated, SignalToOrderHandler(event_bus))

        # Readiness checks, evaluated by the framework's health capability.
        health = container.resolve(HealthCheckRegistry)
        health.register(IBConnectionCheck(ib_adapter))
        health.register(MarketDataCheck(ib_adapter))
        health.register(StrategiesLoadedCheck(container.resolve(StrategyRegistry)))
