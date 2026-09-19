"""Monitor stocks use case - core business logic."""

from power_day_trader.core.strategy_registry import StrategyRegistry
from power_framework.protocols.data import MarketDataProvider
from power_framework.protocols.output import OutputPresenter
from power_framework.protocols.strategy import SignalAggregator
from power_framework.types.market import TickerSymbol, TimeInterval
from power_framework.types.signals import SignalMetadata


class MonitorStocksUseCase:
    """
    Core use case: Monitor stocks and generate trading signals.

    This is pure business logic (inside the hexagon).
    No knowledge of:
    - Interactive Brokers
    - CLI implementation
    - Terminal formatting
    - File formats
    """

    def __init__(
        self,
        data_provider: MarketDataProvider,
        registry: StrategyRegistry,
        aggregator: SignalAggregator,
        output: OutputPresenter,
    ) -> None:
        """Inject dependencies through constructor (ports)."""
        self._data_provider = data_provider
        self._registry = registry
        self._aggregator = aggregator
        self._output = output

    async def execute(
        self,
        symbols: list[TickerSymbol],
        interval: TimeInterval,
    ) -> None:
        """
        Execute the monitoring use case.

        Business logic for monitoring stocks and generating signals.
        """
        await self._output.present_status(
            f"Starting monitoring of {len(symbols)} symbols at {interval} intervals"
        )

        # Stream market data and analyze
        async for bar in self._data_provider.stream_bars(symbols, interval):
            # Apply all strategies to the bar
            signals = []
            for strategy in self._registry.strategies:
                try:
                    signal = await strategy.analyze([bar])
                    signals.append(signal)
                except Exception as e:
                    await self._output.present_error(e)

            # Aggregate signals using business rules
            if signals:
                aggregated = self._aggregator.aggregate_signals(signals)

                # Create metadata
                metadata = SignalMetadata(
                    bars_analyzed=1,
                    computation_time_ms=0.0,  # TODO: Track time
                    indicators={},
                )

                # Present result
                await self._output.present_signal(bar.symbol, aggregated, metadata)
