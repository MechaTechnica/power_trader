"""Registry aggregating all loaded trading strategies."""

from typing import Any

from power_framework.protocols.lifecycle import Lifecycle
from power_market.protocols.strategy import Strategy


class StrategyRegistry(Lifecycle):
    """Holds every registered strategy and drives their lifecycle.

    The container injects every ``Strategy[T]`` specialization as a list. As a
    single :class:`Lifecycle` component, the runtime starts/stops this registry
    in order. Only strategies that opt into :class:`Lifecycle` are driven.
    """

    def __init__(self, strategies: list[Strategy[Any]]) -> None:
        self._strategies = strategies

    @property
    def strategies(self) -> list[Strategy[Any]]:
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
