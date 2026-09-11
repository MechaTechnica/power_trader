"""Infrastructure wiring for the momentum strategy.

The strategy itself (a pure domain concept) stays free of container concerns.
This plugin registers the strategy and its dependencies into the container it
is handed by the runtime.
"""

from power_trader_framework.plugins import PluginBase
from power_trader_framework.protocols.container import IContainer
from power_trader_framework.protocols.strategy import IStrategy
from power_trader_strategy_momentum.strategy import MomentumStrategy


class MomentumPlugin(PluginBase):
    """Plugin wiring for the momentum strategy."""

    def on_register(self, container: IContainer) -> None:
        container.register(IStrategy, MomentumStrategy)
