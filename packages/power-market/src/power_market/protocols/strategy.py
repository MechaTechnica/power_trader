"""Strategy protocols for ML trading strategies."""

from typing import Protocol, TypeVar

from power_market.types.market import MarketBar
from power_market.types.signals import TradingSignal

#: Discriminator type parameter. Each strategy registers itself under a
#: distinct ``Strategy[T]`` specialization (``T`` is typically its own
#: implementation type), letting the container hold many strategies without
#: key collisions. The container can then resolve *all* of them as a list.
T = TypeVar("T")


class Strategy(Protocol[T]):
    """
    Protocol for ML trading strategies (plugins).

    Each strategy is a separate package that implements this protocol. A
    strategy is a pure *domain concept* - infrastructure wiring (registering
    its dependencies into a container) lives in the strategy package's
    ``plugin.py``, not here.
    """

    @property
    def strategy_name(self) -> str:
        """
        Unique identifier for this strategy.

        Returns:
            Strategy name (e.g., "momentum-v1")
        """
        ...

    @property
    def version(self) -> str:
        """
        Strategy version.

        Returns:
            Version string (e.g., "1.0.0")
        """
        ...

    async def analyze(self, bars: list[MarketBar]) -> TradingSignal:
        """
        Analyze market data and generate trading signal.

        Args:
            bars: Historical market bars (ordered oldest to newest)
                  The last bar is the most recent

        Returns:
            TradingSignal with BUY, HOLD, or SELL recommendation

        Note:
            This is called frequently (hot path), so performance matters.
            Strategies should:
            - Cache computed indicators when possible
            - Avoid blocking I/O
            - Return quickly (< 100ms ideal)
        """
        ...

    async def initialize(self) -> None:
        """
        Initialize strategy.

        Called once when strategy is loaded.
        Use for:
        - Loading ML models
        - Warming up caches
        - Validating configuration
        """
        ...

    async def cleanup(self) -> None:
        """
        Cleanup strategy resources.

        Called when strategy is unloaded or application shuts down.
        """
        ...


class SignalAggregator(Protocol):
    """
    Protocol for aggregating signals from multiple strategies.

    When multiple strategies provide signals for the same stock,
    this combines them into a single signal using business rules.
    """

    def aggregate_signals(
        self,
        signals: list[TradingSignal],
    ) -> TradingSignal:
        """
        Combine multiple strategy signals into one.

        Args:
            signals: List of signals from different strategies
                     All signals are for the same stock/timestamp

        Returns:
            Aggregated signal

        Note:
            Implementation defines the aggregation strategy:
            - Weighted average by confidence
            - Unanimous decision only
            - Majority voting
            - Custom ML-based aggregation
        """
        ...
