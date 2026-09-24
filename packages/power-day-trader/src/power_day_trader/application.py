"""Power Day Trader application lifecycle."""

from power_day_trader.adapters.primary.cli_adapter import CLIAdapter
from power_framework.application import ApplicationBase
from power_framework.observability import StructuredLogger, TerminalLogger
from power_framework.protocols.output import OutputPresenter


class PowerDayTraderApplication(ApplicationBase):
    """Power Day Trader application lifecycle and run entry point.

    Dependencies are injected through the constructor by the framework. The
    application itself has no knowledge of the DI container. Its ``start`` and
    ``stop`` handle only application-level concerns; the runtime drives the
    infrastructure and domain-service components in their own order.
    """

    def __init__(
        self,
        output: OutputPresenter,
        cli: CLIAdapter,
        logger: TerminalLogger,
        structured_logger: StructuredLogger,
    ) -> None:
        self._output = output
        self._cli = cli
        self._logger = logger
        self._structured_logger = structured_logger

    async def start(self) -> None:
        self._logger.info("application_started")
        await self._output.present_status("Power Day Trader started successfully")

    async def stop(self) -> None:
        self._logger.info("application_stopped")
        await self._output.present_status("Power Day Trader shut down")

    async def run(self) -> None:
        await self._cli.run()
