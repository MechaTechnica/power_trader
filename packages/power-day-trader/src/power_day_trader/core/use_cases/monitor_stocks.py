"""Monitor stocks use case - core business logic."""

from power_day_trader.core.strategy_registry import StrategyRegistry
from power_framework.events import EventBus
from power_framework.exceptions import ApplicationError
from power_framework.output import OutputPresenter
from power_market.events import MarketDataReceived, SignalGenerated
from power_market.protocols.data import MarketDataProvider
from power_market.protocols.output import SignalPresenter
from power_market.protocols.strategy import SignalAggregator
from power_market.types.market import MarketContext, TickerSymbol, TimeInterval
from power_market.types.signals import SignalMetadata


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
        signal_presenter: SignalPresenter,
        *,
        event_bus: EventBus,
    ) -> None:
        """Inject dependencies through constructor (ports)."""
        self._data_provider = data_provider
        self._registry = registry
        self._aggregator = aggregator
        self._output = output
        self._signal_presenter = signal_presenter
        self._event_bus = event_bus

    async def execute(
        self,
        symbols: list[TickerSymbol],
        interval: TimeInterval,
    ) -> None:
        """
        Execute the monitoring use case.

        Business logic for monitoring stocks and generating signals.
        """
        self._output.present_status(
            f"Starting monitoring of {len(symbols)} symbols at {interval} intervals"
        )

        # Stream market data and analyze
        async for bar in self._data_provider.stream_bars(symbols, interval):
            # Publish the domain fact that a bar arrived, so decoupled handlers
            # (audit, analytics, persistence) can react without coupling here.
            await self._event_bus.publish(MarketDataReceived(symbol=bar.symbol, bar=bar))

            # Build a market snapshot for the strategies
            context = MarketContext(
                symbol=bar.symbol,
                bars=[bar],
                timestamp=bar.timestamp,
            )

            # Apply all strategies to the market context
            signals = []
            for strategy in self._registry.strategies:
                try:
                    signal = await strategy.analyze(context)
                    signals.append(signal)
                    await self._event_bus.publish(SignalGenerated(symbol=bar.symbol, signal=signal))
                except ApplicationError as e:
                    self._output.present_error(e)

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
                self._signal_presenter.present_signal(bar.symbol, aggregated, metadata)
