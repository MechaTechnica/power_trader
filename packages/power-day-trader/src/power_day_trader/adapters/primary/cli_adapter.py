"""CLI adapter (primary adapter)."""

from collections.abc import Awaitable

import click
from power_day_trader.core.use_cases.monitor_stocks import MonitorStocksUseCase
from power_market.types.market import TickerSymbol, TimeInterval


class CLIAdapter:
    """
    CLI adapter - thin layer that converts CLI input to use case calls.

    This is a primary adapter (driving) that drives the application.

    ``run`` parses command-line arguments synchronously (click is
    synchronous) and then awaits the resulting use-case coroutine on the
    *ambient event loop* owned by the runtime. It never creates its own loop
    via ``asyncio.run``.
    """

    def __init__(self, monitor_use_case: MonitorStocksUseCase) -> None:
        """Inject use case dependency."""
        self._monitor_use_case = monitor_use_case

    async def run(self) -> None:
        """Parse the CLI and await the resolved monitoring action."""
        try:
            coroutine = self.create_cli()(standalone_mode=False)
        except click.ClickException as exc:
            # ``standalone_mode=False`` keeps click from terminating so the
            # async use case can run on the runtime-owned loop, but it also
            # re-raises usage errors instead of exiting. Reproduce click's
            # standalone behaviour here, at the click boundary, so callers
            # (e.g. ``main``) stay free of click-specific handling.
            exc.show()
            raise SystemExit(exc.exit_code) from exc
        if coroutine is not None:
            await coroutine

    def create_cli(self) -> click.Group:
        """Create Click CLI with commands."""

        @click.group()
        def cli() -> None:
            """Power Day Trader - Day trading with ML strategies."""

        @cli.command()
        @click.argument("symbols", nargs=-1, required=False)
        @click.option(
            "--symbols",
            "symbol_options",
            multiple=True,
            help="Stock symbol to monitor (repeatable; alternative to positional args).",
        )
        @click.option(
            "--interval",
            "-i",
            default=60,
            type=int,
            help="Time interval in seconds (default: 60)",
        )
        def monitor(
            symbols: tuple[str, ...],
            symbol_options: tuple[str, ...],
            interval: int,
        ) -> Awaitable[None]:
            """Monitor stocks for trading signals.

            Symbols may be given positionally (``monitor AAPL MSFT``) or via
            the repeatable ``--symbols`` option (``monitor --symbols AAPL
            --symbols MSFT``).
            """
            all_symbols = [*symbols, *symbol_options]
            if not all_symbols:
                raise click.UsageError(
                    "At least one symbol is required (positional or --symbols)."
                )

            # Convert CLI types to domain types
            ticker_symbols = [TickerSymbol(symbol=s.upper()) for s in all_symbols]
            time_interval = TimeInterval.from_seconds(interval)

            # Return the coroutine for the runtime to await; do not run a loop here.
            return self._monitor_use_case.execute(ticker_symbols, time_interval)

        return cli
