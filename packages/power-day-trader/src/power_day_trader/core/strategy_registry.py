"""Registry aggregating all loaded trading strategies."""

from power_framework.protocols.lifecycle import Lifecycle
from power_market.protocols.strategy import Strategy


class StrategyRegistry(Lifecycle):
    """Holds every registered strategy and drives their lifecycle.

    The container injects ``list[Strategy]`` (every ``Strategy[T]``
    specialization) into this service. As a single :class:`Lifecycle`
    component, the runtime starts/stops this registry in a consistent order.

    Lifecycle is *not* part of the :class:`Strategy` domain interface, so the
    registry only drives ``start``/``stop`` on strategies that separately opt
    into the framework :class:`Lifecycle` protocol.
    """

    def __init__(self, strategies: list[Strategy]) -> None:
        self._strategies = strategies

    @property
    def strategies(self) -> list[Strategy]:
        """All strategies, in registration order."""
        return self._strategies

    async def start(self) -> None:
        """Start every strategy that implements the lifecycle protocol."""
        for strategy in self._strategies:
            if isinstance(strategy, Lifecycle):
                await strategy.start()

    async def stop(self) -> None:
        """Stop every strategy that implements the lifecycle protocol."""
        for strategy in self._strategies:
            if isinstance(strategy, Lifecycle):
                await strategy.stop()
