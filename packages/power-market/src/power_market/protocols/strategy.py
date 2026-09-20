"""Strategy protocols for ML trading strategies."""

from typing import Protocol, TypeVar

from power_market.types.market import MarketContext
from power_market.types.signals import Signal

#: Discriminator type parameter. Each strategy registers itself under a
#: distinct ``Strategy[T]`` specialization (``T`` is typically its own
#: implementation type), letting the container hold many strategies without
#: key collisions. The container can then resolve *all* of them as a list.
T = TypeVar("T")


class Strategy(Protocol[T]):
    """
    Protocol for ML trading strategies (plugins).

    Each strategy is a separate package that implements this protocol. A
    strategy is a pure *domain concept*: it only exposes its identity
    (``strategy_name``/``version``) and its single domain operation
    (``analyze``). Infrastructure concerns such as lifecycle management live
    elsewhere (see ``power_framework.protocols.lifecycle.Lifecycle``), so this
    interface does not accumulate ``start``/``stop``/``health``/``metrics``
    hooks over time. Wiring (registering dependencies into a container) lives
    in the strategy package's ``plugin.py``, not here.
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

    async def analyze(self, context: MarketContext) -> Signal:
        """
        Analyze market data and generate a trading signal.

        Args:
            context: Market state snapshot (symbol, bars, and reference time).
                     The context is the stable input surface and can evolve to
                     carry quotes, options, fundamentals, news, position, and
                     account state without changing this interface.

        Returns:
            Signal with BUY, HOLD, or SELL intent

        Note:
            This is called frequently (hot path), so performance matters.
            Strategies should:
            - Cache computed indicators when possible
            - Avoid blocking I/O
            - Return quickly (< 100ms ideal)
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
        signals: list[Signal],
    ) -> Signal:
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
