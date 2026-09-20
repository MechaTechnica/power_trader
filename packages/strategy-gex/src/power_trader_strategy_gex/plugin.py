"""Infrastructure wiring for the GEX strategy.

The strategy itself (a pure domain concept) stays free of container concerns.
This plugin registers the strategy and its dependencies into the container it
is handed by the runtime.
"""

from power_framework.plugins import Plugin
from power_framework.protocols.container import Container
from power_framework.protocols.lifecycle import LifecycleRegistry
from power_market.protocols.strategy import Strategy
from power_trader_strategy_gex.gex_calculator import GEXCalculator
from power_trader_strategy_gex.strategy import GEXStrategy


class GEXPlugin(Plugin):
    """Plugin wiring for the GEX strategy."""

    name = "gex"

    def register(self, container: Container, runtime: LifecycleRegistry) -> None:
        del runtime
        container.register(GEXCalculator)
        container.register(Strategy[GEXStrategy], GEXStrategy)
