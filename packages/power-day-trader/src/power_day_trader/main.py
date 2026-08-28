"""Main entry point with dependency injection setup."""

from that_depends import providers

from power_day_trader.adapters.primary.cli_adapter import CLIAdapter
from power_day_trader.adapters.secondary.ib_provider import InteractiveBrokersAdapter
from power_day_trader.adapters.secondary.signal_aggregator import WeightedAverageAggregator
from power_day_trader.adapters.secondary.terminal_output import TerminalOutputAdapter
from power_day_trader.config.settings import Settings
from power_day_trader.core.application import Application
from power_day_trader.core.di_container import DIContainer, PluginRegistry
from power_day_trader.core.use_cases.monitor_stocks import MonitorStocksUseCase


class TradingAppContainer(DIContainer):
    """
    Application DI container with all wiring.
    
    This is where we wire everything together:
    - Which adapters to use
    - How to configure them
    - What gets injected where
    """

    # Configuration
    settings = providers.Singleton(Settings.load)

    # Plugin registry
    plugin_registry = providers.Singleton(PluginRegistry)

    # Secondary adapters (driven - implementations)
    ib_provider = providers.Singleton(
        InteractiveBrokersAdapter,
        host=settings.provided.ib.host,
        port=settings.provided.ib.port,
        client_id=settings.provided.ib.client_id,
    )

    terminal_output = providers.Singleton(TerminalOutputAdapter)

    signal_aggregator = providers.Singleton(WeightedAverageAggregator)

    # Strategies (discovered from plugins)
    @providers.Singleton
    @staticmethod
    def strategies(plugin_registry: PluginRegistry) -> list:  # type: ignore
        """Get all registered strategy instances."""
        return plugin_registry.get_all_strategies()

    # Core use cases
    monitor_use_case = providers.Singleton(
        MonitorStocksUseCase,
        data_provider=ib_provider,
        strategies=strategies,
        aggregator=signal_aggregator,
        output=terminal_output,
    )

    # Primary adapters (driving)
    cli_adapter = providers.Singleton(CLIAdapter, monitor_use_case=monitor_use_case)


def create_app() -> Application:
    """
    Create and configure application.
    
    Returns:
        Configured Application instance
    """
    container = TradingAppContainer()
    app = Application(container)

    # Register lifecycle hooks
    async def on_startup() -> None:
        """Startup tasks."""
        # Discover strategy plugins
        plugin_registry = container.plugin_registry()
        plugin_registry.discover_strategies()
        await plugin_registry.initialize_all()

        # Connect to IB
        ib_provider = container.ib_provider()
        await ib_provider.connect()

        output = container.terminal_output()
        await output.present_status("Application started successfully")

    async def on_shutdown() -> None:
        """Shutdown tasks."""
        # Cleanup strategies
        plugin_registry = container.plugin_registry()
        await plugin_registry.cleanup_all()

        # Disconnect from IB
        ib_provider = container.ib_provider()
        await ib_provider.disconnect()

        output = container.terminal_output()
        await output.present_status("Application shut down")

    app.on_startup(on_startup)
    app.on_shutdown(on_shutdown)

    return app


def cli() -> None:
    """CLI entry point."""
    container = TradingAppContainer()
    cli_adapter = container.cli_adapter()
    click_cli = cli_adapter.create_cli()
    click_cli()


if __name__ == "__main__":
    cli()
