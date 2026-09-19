"""Plugin base class.

A plugin encapsulates a strategy's or application's *infrastructure wiring*:
it registers services (and itself) into the container it is given by the
runtime.
"""

from __future__ import annotations

import importlib.metadata
from abc import ABC, abstractmethod
from collections.abc import Callable
from functools import lru_cache
from typing import ClassVar, cast

from power_trader_framework.protocols.container import Container

#: Predicate applied to an entry point's name during discovery.
EntryPointPredicate = Callable[[str], bool]


class Plugin(ABC):
    """Base class for plugins (strategies and applications).
    Plugins are intentionally small composition units.
    """

    name: ClassVar[str | None] = None

    @abstractmethod
    def register(self, container: Container) -> None:
        """Register this plugin's services into ``container``."""


@lru_cache(maxsize=1)
def _get_entry_points() -> importlib.metadata.EntryPoints | importlib.metadata.SelectableGroups:
    """Return all installed entry points, cached.

    Entry points are fixed for the lifetime of the process after package
    installation, so the result is safe to memoize.
    """
    return importlib.metadata.entry_points()


def _filter_entry_points(
    entry_points: importlib.metadata.EntryPoints | importlib.metadata.SelectableGroups,
    group: str,
    predicate: EntryPointPredicate,
) -> list[importlib.metadata.EntryPoint]:
    """Return the entry points in ``group`` whose name satisfies ``predicate``."""
    if hasattr(entry_points, "select"):
        entries = entry_points.select(group=group)
    else:  # Legacy ``entry_points()`` returns a ``defaultdict`` without ``select``.
        entries = cast("importlib.metadata.SelectableGroups", entry_points).get(
            group, importlib.metadata.EntryPoints()
        )
    return [entry_point for entry_point in entries if predicate(entry_point.name)]
