"""Power Day Trader application lifecycle."""

from power_day_trader.adapters.primary.cli_adapter import CLIAdapter
from power_day_trader.core.strategy_registry import StrategyRegistry
from power_framework.application import ApplicationBase
from power_framework.protocols.data import MarketDataProvider
from power_framework.protocols.output import OutputPresenter


class PowerDayTraderApplication(ApplicationBase):
    """Power Day Trader application lifecycle and run entry point."""

    async def on_startup(self) -> None:
        ib_provider = self.application_model.container.resolve(MarketDataProvider)
        await ib_provider.connect()

        output = self.application_model.container.resolve(OutputPresenter)
        await output.present_status("Power Day Trader started successfully")

    async def on_shutdown(self) -> None:
        ib_provider = self.application_model.container.resolve(MarketDataProvider)
        await ib_provider.disconnect()

        output = self.application_model.container.resolve(OutputPresenter)
        await output.present_status("Power Day Trader shut down")
        await self.application_model.container.resolve(StrategyRegistry).cleanup()

    def run(self) -> None:
        cli_adapter = self.application_model.container.resolve(CLIAdapter)
        cli_adapter.create_cli()()
