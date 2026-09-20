"""Plugin base class.

A plugin is a component loaded dynamically that is part of a larger system.
"""

from __future__ import annotations

import importlib.metadata
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import TYPE_CHECKING, ClassVar, cast

if TYPE_CHECKING:
    from power_framework.protocols.container import Container
    from power_framework.protocols.lifecycle import LifecycleRegistry
    from power_framework.settings import Settings


class Plugin(ABC):
    """Base class for plugins (strategies and applications).
    Plugins are intentionally small composition units.
    """

    name: ClassVar[str | None] = None

    #: Optional application settings model. When set, the framework loads it
    #: (environment + JSON file) and registers it in the container *before*
    #: calling :meth:`register`, so the plugin consumes configuration rather
    #: than loading it itself.
    settings_class: ClassVar[type[Settings] | None] = None

    @abstractmethod
    def register(self, container: Container, runtime: LifecycleRegistry) -> None:
        """Register this plugin's services into ``container``.

        Lifecycle components should additionally be registered into ``runtime``
        in start order, so the runtime owns their ordering.
        """


@lru_cache(maxsize=1)
def _get_entry_points() -> importlib.metadata.EntryPoints | importlib.metadata.SelectableGroups:
    """Return all installed entry points, cached.

    Entry points are fixed for the lifetime of the process after package
    installation, so the result is safe to memoize.
    """
    return importlib.metadata.entry_points()


def _get_group_entry_points(
    entry_points: importlib.metadata.EntryPoints | importlib.metadata.SelectableGroups,
    group: str,
) -> list[importlib.metadata.EntryPoint]:
    """Return every entry point registered in ``group``."""
    if hasattr(entry_points, "select"):
        entries = entry_points.select(group=group)
    else:  # Legacy ``entry_points()`` returns a ``defaultdict`` without ``select``.
        entries = cast("importlib.metadata.SelectableGroups", entry_points).get(
            group, importlib.metadata.EntryPoints()
        )
    return list(entries)
