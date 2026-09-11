"""Plugin base class for strategy plugins.

A plugin encapsulates a strategy's *infrastructure wiring*. The strategy
itself stays a pure domain concept; the plugin registers the strategy (and
any dependencies it wishes to expose) into the container it is given by the
runtime.
"""

from abc import ABC, abstractmethod

from power_trader_framework.protocols.container import IContainer


class PluginBase(ABC):
    """Base class for strategy plugins."""

    @abstractmethod
    def on_register(self, container: IContainer) -> None:
        """Register this plugin's strategy and services into ``container``."""
        ...
