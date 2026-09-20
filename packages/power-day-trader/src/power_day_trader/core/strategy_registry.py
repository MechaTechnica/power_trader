"""Registry aggregating all loaded trading strategies."""

from power_framework.protocols.lifecycle import Lifecycle
from power_market.protocols.strategy import Strategy


class StrategyRegistry(Lifecycle):
    """Holds every registered strategy and drives their lifecycle.

    The container injects ``list[Strategy]`` (every ``Strategy[T]``
    specialization) into this service. As a single :class:`Lifecycle`
    component, the runtime starts/stops all strategies in a consistent order
    rather than having the application coordinate them individually.
    """

    def __init__(self, strategies: list[Strategy]) -> None:
        self._strategies = strategies

    @property
    def strategies(self) -> list[Strategy]:
        """All strategies, in registration order."""
        return self._strategies

    async def start(self) -> None:
        """Start every strategy in registration order."""
        for strategy in self._strategies:
            await strategy.start()

    async def stop(self) -> None:
        """Stop every strategy in registration order."""
        for strategy in self._strategies:
            await strategy.stop()
