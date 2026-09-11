"""Plugin base class.

A plugin encapsulates a strategy's or application's *infrastructure wiring*:
it registers services (and itself) into the container it is given by the
runtime.
"""

from abc import ABC, abstractmethod

from power_trader_framework.protocols.container import Container


class Plugin(ABC):
    """Base class for plugins (strategies and applications)."""

    @abstractmethod
    def on_register(self, container: Container) -> None:
        """Register this plugin's services into ``container``."""
        ...
