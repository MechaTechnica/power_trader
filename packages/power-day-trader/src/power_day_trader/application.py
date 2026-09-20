"""Power Day Trader application lifecycle."""

from power_day_trader.adapters.primary.cli_adapter import CLIAdapter
from power_day_trader.core.strategy_registry import StrategyRegistry
from power_framework.application import ApplicationBase
from power_framework.protocols.output import OutputPresenter
from power_market.protocols.data import MarketDataProvider


class PowerDayTraderApplication(ApplicationBase):
    """Power Day Trader application lifecycle and run entry point.

    Dependencies are injected through the constructor by the framework. The
    application itself has no knowledge of the DI container.
    """

    def __init__(self, market_data: MarketDataProvider, output: OutputPresenter, strategies: StrategyRegistry, cli: CLIAdapter) -> None:
        self._market_data = market_data
        self._output = output
        self._strategies = strategies
        self._cli = cli

    async def on_startup(self) -> None:
        await self._market_data.connect()
        await self._output.present_status("Power Day Trader started successfully")

    async def on_shutdown(self) -> None:
        await self._market_data.disconnect()
        await self._output.present_status("Power Day Trader shut down")
        await self._strategies.cleanup()

    def run(self) -> None:
        self._cli.create_cli()()
