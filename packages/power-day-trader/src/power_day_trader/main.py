"""Main entry point for Power Day Trader."""

from functools import lru_cache

from power_day_trader.adapters.primary.cli_adapter import CLIAdapter
from power_day_trader.adapters.secondary.ib_provider import \
    InteractiveBrokersAdapter
from power_day_trader.adapters.secondary.signal_aggregator import \
    WeightedAverageAggregator
from power_day_trader.adapters.secondary.terminal_output import \
    TerminalOutputAdapter
from power_day_trader.config.settings import ApplicationSettings
from power_day_trader.core.use_cases.monitor_stocks import MonitorStocksUseCase
from power_trader_framework.application import ApplicationBase
from power_trader_framework.protocols.container import IContainer
from power_trader_framework.protocols.data import IMarketDataProvider
from power_trader_framework.protocols.output import IOutputPresenter
from power_trader_framework.protocols.plugin import IPluginRegistry
from power_trader_framework.protocols.strategy import (ISignalAggregator,
                                                       IStrategy)
from power_trader_framework.settings import FrameworkSettings


class PowerDayTraderApplication(ApplicationBase):
    """
    Power Day Trader application.

    ``ApplicationBase`` (from ``power_trader_framework``) owns creation of the
    container, loading of ``FrameworkSettings``, and construction of the plugin
    registry - these come from the concrete runtime (``power-core``) via a
    framework entry point, so this module never imports ``power_core``. This
    class only implements the lifecycle hooks the framework invokes.
    """

    def __init__(self) -> None:
        super().__init__()
        self._plugin_registry: IPluginRegistry | None = None

    def on_register(
        self,
        container: IContainer,
        framework_settings: FrameworkSettings,
        plugin_registry: IPluginRegistry,
    ) -> None:
        """Register Power Day Trader's dependencies against the container.

        Registers *interface types* against concrete *implementations*.
        Resolving a type (e.g. ``container.resolve(CLIAdapter)``) builds the
        dependency graph from constructor type hints.
        """
        self._plugin_registry = plugin_registry

        # Application-level configuration (distinct from framework_settings,
        # which the runtime already registered on our behalf).
        app_settings = ApplicationSettings.load()
        container.register_instance(ApplicationSettings, app_settings)

        # Secondary adapters (driven - implementations)
        container.register(
            IMarketDataProvider,
            InteractiveBrokersAdapter,
            host=app_settings.ib.host,
            port=app_settings.ib.port,
            client_id=app_settings.ib.client_id,
        )
        container.register(IOutputPresenter, TerminalOutputAdapter)
        container.register(ISignalAggregator, WeightedAverageAggregator)

        # Strategies (discovered from plugins via the registry the runtime
        # already created and registered for us).
        container.register(
            list[IStrategy],
            lambda registry: registry.get_all_strategies(),
            registry=plugin_registry,
        )

        # Core use cases (concrete types registered by type)
        container.register(MonitorStocksUseCase, MonitorStocksUseCase)

        # Primary adapters (driving)
        container.register(CLIAdapter, CLIAdapter)

    async def on_startup(self) -> None:
        """Startup tasks."""
        container = self.container

        plugin_registry = self._plugin_registry
        assert plugin_registry is not None
        plugin_registry.discover_strategies()
        await plugin_registry.initialize_all()

        ib_provider: IMarketDataProvider = container.resolve(IMarketDataProvider)
        await ib_provider.connect()

        output: IOutputPresenter = container.resolve(IOutputPresenter)
        await output.present_status("Power Day Trader started successfully")

    async def on_shutdown(self) -> None:
        """Shutdown tasks."""
        container = self.container

        plugin_registry = self._plugin_registry
        assert plugin_registry is not None
        await plugin_registry.cleanup_all()

        ib_provider: IMarketDataProvider = container.resolve(IMarketDataProvider)
        await ib_provider.disconnect()

        output: IOutputPresenter = container.resolve(IOutputPresenter)
        await output.present_status("Power Day Trader shut down")


@lru_cache(maxsize=1)
def get_application() -> PowerDayTraderApplication:
    """Return the shared, framework-built application (built lazily, cached)."""
    app = PowerDayTraderApplication()
    app.build()
    return app


def cli() -> None:
    """CLI entry point."""
    app = get_application()
    cli_adapter: CLIAdapter = app.container.resolve(CLIAdapter)
    click_cli = cli_adapter.create_cli()
    click_cli()


if __name__ == "__main__":
    cli()
