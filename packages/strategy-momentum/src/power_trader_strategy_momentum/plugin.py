"""Infrastructure wiring for the momentum strategy.

The strategy itself (a pure domain concept) stays free of container concerns.
This plugin registers the strategy and its dependencies into the container it
is handed by the runtime.
"""

from power_framework.plugins import Plugin
from power_framework.protocols.container import Container
from power_framework.protocols.lifecycle import LifecycleRegistry
from power_market.protocols.strategy import Strategy
from power_trader_strategy_momentum.strategy import MomentumStrategy


class MomentumPlugin(Plugin):
    """Plugin wiring for the momentum strategy."""

    name = "momentum"

    def register(self, container: Container, runtime: LifecycleRegistry) -> None:
        container.register(Strategy[MomentumStrategy], MomentumStrategy)
