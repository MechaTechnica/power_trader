"""Registry aggregating all loaded trading strategies."""

from power_trader_framework.protocols.strategy import Strategy


class StrategyRegistry:
    """Holds every registered strategy and orchestrates their lifecycle.

    The container injects ``list[Strategy]`` (every ``Strategy[T]``
    specialization) into this service, giving the application a single place to
    enumerate strategies and run their shutdown hooks.
    """

    def __init__(self, strategies: list[Strategy]) -> None:
        self._strategies = strategies

    @property
    def strategies(self) -> list[Strategy]:
        """All strategies, in registration order."""
        return self._strategies

    async def cleanup(self) -> None:
        """Run each strategy's ``cleanup`` hook."""
        for strategy in self._strategies:
            await strategy.cleanup()