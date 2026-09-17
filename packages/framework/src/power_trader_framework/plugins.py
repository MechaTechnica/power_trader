"""Plugin base class.

A plugin encapsulates a strategy's or application's *infrastructure wiring*:
it registers services (and itself) into the container it is given by the
runtime.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from power_trader_framework.protocols.container import Container


class Plugin(ABC):
    """Base class for plugins (strategies and applications).
    Plugins are intentionally small composition units.  
    """

    name: ClassVar[str | None] = None

    @abstractmethod
    def register(self, container: Container) -> None:
        """Register this plugin's services into ``container``."""
        ...
