"""Infrastructure wiring for the GEX strategy.

The strategy itself (a pure domain concept) stays free of container concerns.
This plugin registers the strategy and its dependencies into the container it
is handed by the runtime.
"""

from power_trader_framework.plugins import PluginBase
from power_trader_framework.protocols.container import IContainer
from power_trader_framework.protocols.strategy import IStrategy
from power_trader_strategy_gex.gex_calculator import GEXCalculator
from power_trader_strategy_gex.strategy import GEXStrategy


class GEXPlugin(PluginBase):
    """Plugin wiring for the GEX strategy."""

    def on_register(self, container: IContainer) -> None:
        container.register(GEXCalculator)
        container.register(IStrategy, GEXStrategy)
