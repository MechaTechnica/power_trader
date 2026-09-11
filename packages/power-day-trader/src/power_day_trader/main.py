"""Main entry point for Power Day Trader."""

from functools import lru_cache

from power_day_trader.adapters.primary.cli_adapter import CLIAdapter
from power_day_trader.adapters.secondary.ib_provider import \
    InteractiveBrokersAdapter
from power_day_trader.adapters.secondary.signal_aggregator import \
    WeightedAverageAggregator
from power_day_trader.adapters.secondary.terminal_output import \
    TerminalOutputAdapter
from power_day_trader.config.settings import PowerTraderSettings
from power_day_trader.core.use_cases.monitor_stocks import MonitorStocksUseCase
from power_trader_framework.application import ApplicationBase
from power_trader_framework.protocols.container import IContainer
from power_trader_framework.protocols.data import IMarketDataProvider
from power_trader_framework.protocols.output import IOutputPresenter
from power_trader_framework.protocols.strategy import ISignalAggregator


class PowerDayTraderApplication(ApplicationBase):
    """
    Power Day Trader application.

    ``ApplicationBase`` (from ``power_trader_framework``) owns the container and
    discovers/builds the strategies. This class registers its own settings,
    output presenter, adapters, and use cases.
    """

    def on_register(self, container: IContainer) -> None:
        """Register app-specific settings, adapters, and use cases."""
        app_settings = PowerTraderSettings.load()
        container.register_instance(PowerTraderSettings, app_settings)
        container.register(IOutputPresenter, TerminalOutputAdapter)

        container.register(
            IMarketDataProvider,
            InteractiveBrokersAdapter,
            host=app_settings.ib.host,
            port=app_settings.ib.port,
            client_id=app_settings.ib.client_id,
        )
        container.register(ISignalAggregator, WeightedAverageAggregator)
        container.register(MonitorStocksUseCase, MonitorStocksUseCase)
        container.register(CLIAdapter, CLIAdapter)

    async def on_startup(self) -> None:
        """Startup: resolve and connect."""
        ib_provider = self.container.resolve(IMarketDataProvider)
        await ib_provider.connect()

        output = self.container.resolve(IOutputPresenter)
        await output.present_status("Power Day Trader started successfully")

    async def on_shutdown(self) -> None:
        """Shutdown: resolve and disconnect."""
        ib_provider = self.container.resolve(IMarketDataProvider)
        await ib_provider.disconnect()

        output = self.container.resolve(IOutputPresenter)
        await output.present_status("Power Day Trader shut down")


@lru_cache(maxsize=1)
def get_application() -> PowerDayTraderApplication:
    app = PowerDayTraderApplication()
    app.build()
    return app


def cli() -> None:
    app = get_application()
    cli_adapter = app.container.resolve(CLIAdapter)
    cli_adapter.create_cli()()


if __name__ == "__main__":
    cli()
