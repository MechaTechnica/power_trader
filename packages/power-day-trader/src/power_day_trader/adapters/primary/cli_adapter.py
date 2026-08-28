"""CLI adapter (primary adapter)."""

import asyncio

import click
from power_day_trader.core.use_cases.monitor_stocks import MonitorStocksUseCase
from power_trader_framework.types.market import TickerSymbol, TimeInterval


class CLIAdapter:
    """
    CLI adapter - thin layer that converts CLI input to use case calls.
    
    This is a primary adapter (driving) that drives the application.
    """

    def __init__(self, monitor_use_case: MonitorStocksUseCase) -> None:
        """Inject use case dependency."""
        self._monitor_use_case = monitor_use_case

    def create_cli(self) -> click.Group:
        """Create Click CLI with commands."""

        @click.group()
        def cli() -> None:
            """Power Day Trader - Day trading with ML strategies."""
            pass

        @cli.command()
        @click.option(
            "--symbols",
            "-s",
            multiple=True,
            required=True,
            help="Stock symbols to monitor (e.g., AAPL MSFT)",
        )
        @click.option(
            "--interval",
            "-i",
            default=60,
            type=int,
            help="Time interval in seconds (default: 60)",
        )
        def monitor(symbols: tuple[str], interval: int) -> None:
            """Monitor stocks for trading signals."""
            # Convert CLI types to domain types
            ticker_symbols = [TickerSymbol(symbol=s.upper()) for s in symbols]
            time_interval = TimeInterval.from_seconds(interval)
            
            # Execute use case
            asyncio.run(self._monitor_use_case.execute(ticker_symbols, time_interval))

        return cli
