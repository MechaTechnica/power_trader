"""Power Day Trader application lifecycle."""

from power_day_trader.adapters.primary.cli_adapter import CLIAdapter
from power_trader_framework.application import ApplicationBase
from power_trader_framework.protocols.data import MarketDataProvider
from power_trader_framework.protocols.output import OutputPresenter


class PowerDayTraderApplication(ApplicationBase):
    """Power Day Trader application lifecycle and run entry point."""

    async def on_startup(self) -> None:
        """Startup: resolve and connect."""
        assert self.container is not None
        ib_provider = self.container.resolve(MarketDataProvider)
        await ib_provider.connect()

        output = self.container.resolve(OutputPresenter)
        await output.present_status("Power Day Trader started successfully")

    async def on_shutdown(self) -> None:
        """Shutdown: resolve and disconnect."""
        assert self.container is not None
        ib_provider = self.container.resolve(MarketDataProvider)
        await ib_provider.disconnect()

        output = self.container.resolve(OutputPresenter)
        await output.present_status("Power Day Trader shut down")

    def run(self) -> None:
        """Run the application: resolve the CLI and dispatch."""
        assert self.container is not None
        cli_adapter = self.container.resolve(CLIAdapter)
        cli_adapter.create_cli()()
