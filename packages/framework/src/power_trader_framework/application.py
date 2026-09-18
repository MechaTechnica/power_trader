"""Application builder and runtime discovery.

Applications are described by two pieces:

- a :class:`Plugin` (its wiring, via ``register``), and
- an :class:`ApplicationBase` (its lifecycle and run entry point).

Use :class:`ApplicationBuilder` to assemble and run them:

    app = ApplicationBuilder(MyApplication).build()
    app.run()

The concrete runtime (``Container``)
lives in ``power-core``; the framework discovers it via a package entry point
at build time, so applications depend only on ``power_trader_framework`` -
never on ``power_core`` directly.
"""

from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Union, cast

from power_trader_framework.plugins import Plugin
from power_trader_framework.protocols.container import Container

PLUGIN_GROUP = "power.plugins"
CORE_NAME = "power-core"  # name of the key

#: Predicate applied to an entry point's name during discovery.
EntryPointPredicate = Callable[[str], bool]


@dataclass
class ApplicationModel:
    """The model for an application, containing the container and the constructed application.
    """

    container: Container
    application: ApplicationBase


@lru_cache(maxsize=1)
def _get_entry_points() -> Union[
    importlib.metadata.EntryPoints, importlib.metadata.SelectableGroups]:
    """Return all installed entry points, cached.

    Entry points are fixed for the lifetime of the process after package
    installation, so the result is safe to memoize.
    """
    return importlib.metadata.entry_points()


def _filter_entry_points(
    entry_points: Union[
        importlib.metadata.EntryPoints, importlib.metadata.SelectableGroups
    ],
    group: str,
    predicate: EntryPointPredicate,
) -> list[importlib.metadata.EntryPoint]:
    """Return the entry points in ``group`` whose name satisfies ``predicate``."""
    if hasattr(entry_points, "select"):
        entries = entry_points.select(group=group)
    else:  # Legacy ``entry_points()`` returns a ``defaultdict`` without ``select``.
        entries = cast(importlib.metadata.SelectableGroups, entry_points).get(
            group, importlib.metadata.EntryPoints()
        )
    return [entry_point for entry_point in entries if predicate(entry_point.name)]


def _load_core_entry_point() -> Callable[[type["ApplicationBase"]], ApplicationModel]:
    """Discover power-core's factory from the shared extension-point group."""
    entry_points = _get_entry_points()
    core_matches = _filter_entry_points(
        entry_points, PLUGIN_GROUP, lambda name: name == CORE_NAME
    )

    if not core_matches:
        raise RuntimeError(
            "No framework runtime found. Install 'power-core' and ensure it "
            f"registers the '{PLUGIN_GROUP}' entry point named '{CORE_NAME}'."
        )
    if len(core_matches) > 1:
        raise RuntimeError(
            f"Multiple '{CORE_NAME}' entry points found in group "
            f"'{PLUGIN_GROUP}'. Only one core runtime may be installed."
        )

    return core_matches[0].load()  # type: ignore[no-any-return]


def _load_plugins() -> set[type[Plugin]]:
    """Load and return every installed plugin class in the shared group.

    The ``core`` entry point is the runtime factory rather than a plugin, so it
    is excluded by name. Each loaded object must be a :class:`Plugin` subclass,
    and duplicate registrations (the same plugin class under multiple entry
    points) are returned only once.
    """
    entry_points = _get_entry_points()
    plugin_entries = _filter_entry_points(
        entry_points, PLUGIN_GROUP, lambda name: name != CORE_NAME
    )

    plugins: set[type[Plugin]] = set()
    for entry_point in sorted(plugin_entries, key=lambda candidate: candidate.name):
        plugin_class = entry_point.load()
        if not isinstance(plugin_class, type) or not issubclass(plugin_class, Plugin):
            raise TypeError(
                f"Plugin entry point '{entry_point.name}' must expose a Plugin subclass"
            )
        plugins.add(plugin_class)
    return plugins


class ApplicationBase:
    """Base class for an application's lifecycle and run entry point.

    Subclasses override ``on_startup``, ``on_shutdown``, and ``run``. The
    framework supplies the container through which services can be resolved.
    """

    def __init__(self) -> None:
        self._application_model: ApplicationModel | None = None

    @property
    def application_model(self) -> ApplicationModel:
        application_model = self._application_model
        if application_model is None:
            raise RuntimeError(
                "Application has not been built; no application model available."
            )
        return application_model

    @application_model.setter
    def application_model(self, application_model: ApplicationModel) -> None:
        self._application_model = application_model

    async def on_startup(self) -> None:
        return None

    async def on_shutdown(self) -> None:
        return None

    def run(self) -> None:
        return None


class ApplicationBootstrapper:
    """Assemble plugins, a runtime, and an application instance.

    This class bridges the framework's plugin discovery with the concrete
    runtime (``power-core``) discovered via entry points, reading the built
    container back into the application.
    """

    @staticmethod
    def _initialize_plugins() -> list[Plugin]:
        """Instantiate one instance of every installed plugin."""
        return [plugin_class() for plugin_class in _load_plugins()]

    @staticmethod
    def _create_runtime(application_class: type["ApplicationBase"]) -> ApplicationModel:
        core_entry_point = _load_core_entry_point()
        # The core runtime is responsible for creating the concrete
        # Application instance and wiring the ApplicationModel into it.
        return core_entry_point(application_class)

    @staticmethod
    def bootstrap(application_class: type[ApplicationBase]) -> ApplicationBase:
        """Build the runtime (in core), initialize plugins and return the created
        application instance.
        """
        application_model = ApplicationBootstrapper._create_runtime(application_class)
        application_model.application.application_model = application_model
        for plugin in ApplicationBootstrapper._initialize_plugins():
            plugin.register(application_model.container)
        return application_model.application


class ApplicationBuilder:
    """Fluent builder that assembles an application from plugins and an app."""

    def __init__(self, application_class: type[ApplicationBase]) -> None:
        self._application_class = application_class

    def build(self) -> ApplicationBase:
        """Build the application: container, framework services, plugins, app."""
        return ApplicationBootstrapper.bootstrap(self._application_class)


__all__ = [
    "ApplicationBase",
    "ApplicationBuilder",
    "ApplicationModel",
]
