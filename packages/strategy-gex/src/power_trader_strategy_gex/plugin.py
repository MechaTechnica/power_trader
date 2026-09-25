"""Infrastructure wiring for the GEX strategy.

The strategy itself (a pure domain concept) stays free of container concerns.
This plugin registers the strategy and its dependencies into the container it
is handed by the runtime.
"""

from power_framework.plugins import Plugin, PluginMetadata
from power_framework.protocols.container import Container
from power_market.protocols.strategy import Strategy
from power_trader_strategy_gex.gex_calculator import GEXCalculator
from power_trader_strategy_gex.strategy import GEXStrategy


class GEXPlugin(Plugin):
    """Plugin wiring for the GEX strategy."""

    metadata = PluginMetadata(
        name="gex",
        version="0.1.0",
        description="Gamma Exposure (GEX) trading strategy"
    )

    def register(self, container: Container) -> None:
        container.register(GEXCalculator)
        container.register(Strategy[GEXStrategy], GEXStrategy)
