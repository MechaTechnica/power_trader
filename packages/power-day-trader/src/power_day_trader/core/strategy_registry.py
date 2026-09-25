"""Registry aggregating all loaded trading strategies."""

from typing import Any

from power_market.protocols.strategy import Strategy


class StrategyRegistry:
    """Holds every registered strategy and drives their lifecycle.

    The container injects every ``Strategy[T]`` specialization as a list. The
    registry drives each strategy's ``start``/``stop`` on startup and shutdown.
    """

    def __init__(self, strategies: list[Strategy[Any]]) -> None:
        self._strategies = strategies

    @property
    def strategies(self) -> list[Strategy[Any]]:
        """All strategies, in registration order."""
        return self._strategies

    async def start(self) -> None:
        """Start every strategy."""
        for strategy in self._strategies:
            await strategy.start()

    async def stop(self) -> None:
        """Stop every strategy."""
        for strategy in self._strategies:
            await strategy.stop()
