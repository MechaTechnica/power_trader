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

    Plugins are intentionally small composition units.  Third-party plugins
    are published through Python entry points and should set ``name`` to a
    stable, human-readable identifier.  The runtime validates that identifier
    against the entry-point name, preventing a package from silently replacing
    a different plugin.
    """

    #: Optional stable plugin identifier. Entry-point plugins should provide it.
    name: ClassVar[str | None] = None

    @abstractmethod
    def register(self, container: Container) -> None:
        """Register this plugin's services into ``container``."""
        ...
