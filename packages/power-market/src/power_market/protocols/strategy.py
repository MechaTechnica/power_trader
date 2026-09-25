"""Trading strategy protocols."""

from typing import Protocol, TypeVar

from power_market.types.market import MarketContext
from power_market.types.signals import Signal

#: Discriminator type parameter. Each strategy registers under a distinct
#: ``Strategy[T]`` specialization so the container can hold many strategies
#: without key collisions and resolve all of them as a list.
T_co = TypeVar("T_co", covariant=True)


class Strategy(Protocol[T_co]):
    """A domain strategy: an identity, an ``analyze`` operation, and lifecycle.

    Strategies own their ``start``/``stop`` so a registry can drive them
    uniformly. Wiring goes in the strategy package's ``plugin.py``.
    """

    @property
    def strategy_name(self) -> str:
        """Unique name, e.g. ``"momentum-v1"``."""
        ...

    @property
    def version(self) -> str:
        """Version string, e.g. ``"1.0.0"``."""
        ...

    async def analyze(self, context: MarketContext) -> Signal:
        """Analyze market state and return a BUY/HOLD/SELL signal.

        Called on the hot path, so implementations should cache indicators and
        avoid blocking I/O.
        """
        ...

    async def start(self) -> None:
        """Prepare the strategy for analysis (load models, warm caches)."""
        ...

    async def stop(self) -> None:
        """Release the strategy's resources."""
        ...


class SignalAggregator(Protocol):
    """Combines signals from multiple strategies into one."""

    def aggregate_signals(self, signals: list[Signal]) -> Signal:
        """Merge ``signals`` (same stock/timestamp) into a single signal."""
        ...
