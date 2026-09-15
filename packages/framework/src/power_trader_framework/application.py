"""Application builder and runtime discovery.

Applications are described by two pieces:

- a :class:`Plugin` (its wiring, via ``register``), and
- an :class:`ApplicationBase` (its lifecycle and run entry point).

Use :class:`ApplicationBuilder` to assemble and run them:

    app = ApplicationBuilder(MyApplication).build()
    app.run()

The concrete runtime (``Container`` and ``Application``)
lives in ``power-core``; the framework discovers it via a package entry point
at build time, so applications depend only on ``power_trader_framework`` -
never on ``power_core`` directly.
"""

from __future__ import annotations

import importlib.metadata
from functools import lru_cache
from typing import Awaitable, Callable, Protocol

from power_trader_framework.plugins import Plugin
from power_trader_framework.protocols.container import Container

PLUGIN_GROUP = "power.plugins"
CORE_NAME = "power-core"  # name of the key

#: Predicate applied to an entry point's name during discovery.
EntryPointPredicate = Callable[[str], bool]

class ApplicationRuntime(Protocol):
    """Protocol for the runtime application object produced by power-core."""

    container: Container

    def on_startup(self, func: Callable[[], Awaitable[None]]) -> None: ...

    def on_shutdown(self, func: Callable[[], Awaitable[None]]) -> None: ...

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def run(self) -> None: ...


ConfigureContainer = Callable[[Container], None]

#: Callback applications implement to configure lifecycle hooks after the
#: ``Application`` has been created.
OnAppCreated = Callable[[ApplicationRuntime], None]


@lru_cache(maxsize=1)
def _get_entry_points() -> importlib.metadata.EntryPoints:
    """Return all installed entry points, cached.

    Entry points are fixed for the lifetime of the process after package
    installation, so the result is safe to memoize.
    """
    return importlib.metadata.entry_points()


def _filter_entry_points(
    entry_points: importlib.metadata.EntryPoints,
    group: str,
    predicate: EntryPointPredicate,
) -> list[importlib.metadata.EntryPoint]:
    """Return the entry points in ``group`` whose name satisfies ``predicate``."""
    if hasattr(entry_points, "select"):
        entries = entry_points.select(group=group)
    else:  # Legacy ``entry_points()`` returns a ``defaultdict`` without ``select``.
        entries = entry_points.get(group, ())  # type: ignore[attr-defined]
    return [entry_point for entry_point in entries if predicate(entry_point.name)]


def _load_runtime_factory() -> Callable[..., ApplicationRuntime]:
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


def _load_plugin_factories() -> list[type[Plugin]]:
    """Load and return every installed plugin class in the shared group.

    The ``core`` entry point is the runtime factory rather than a plugin, so it
    is excluded by name. Results are returned in deterministic (name-sorted)
    order, and each loaded object must be a :class:`Plugin` subclass.
    """
    entry_points = _get_entry_points()
    plugin_entries = _filter_entry_points(
        entry_points, PLUGIN_GROUP, lambda name: name != CORE_NAME
    )

    plugins: list[type[Plugin]] = []
    for entry_point in sorted(plugin_entries, key=lambda candidate: candidate.name):
        plugin_class = entry_point.load()
        if not isinstance(plugin_class, type) or not issubclass(plugin_class, Plugin):
            raise TypeError(
                f"Plugin entry point '{entry_point.name}' must expose a Plugin subclass"
            )
        plugins.append(plugin_class)
    return plugins


class ApplicationBase:
    """
    Base class for an application's lifecycle and run entry point.

    Subclasses override ``on_startup``, ``on_shutdown``, and ``run``. The
    framework sets ``container`` during the build so these hooks can resolve
    services.
    """

    container: Container | None = None

    async def on_startup(self) -> None:
        """Startup tasks. Default is a no-op."""
        return None

    async def on_shutdown(self) -> None:
        """Shutdown tasks. Default is a no-op."""
        return None

    def run(self) -> None:
        """Run the application's entry point. Default is a no-op."""
        return None


class Application:
    """A built application, produced by :meth:`ApplicationBuilder.build`."""

    def __init__(self, runtime: ApplicationRuntime, application: ApplicationBase) -> None:
        self._runtime = runtime
        self._application = application

    @property
    def container(self) -> Container:
        """The DI container, with all services registered."""
        return self._runtime.container

    def run(self) -> None:
        """Run the application's entry point."""
        self._application.run()


class ApplicationBuilder:
    """Fluent builder that assembles an application from plugins and an app."""

    def __init__(self, application_class: type[ApplicationBase]) -> None:
        self._application_class = application_class

    def __initialize_plugins(self):
        return [plugin_class() for plugin_class in _load_plugin_factories()]

    def __create_runtime(self, configure_container: ConfigureContainer, on_app_created: OnAppCreated | None = None) -> ApplicationRuntime:
        factory = _load_runtime_factory()
        return factory(configure_container, on_app_created)

    def build(self) -> Application:
        """Build the application: container, framework services, plugins, app."""
        application = self._application_class()

        def configure_container(container: Container) -> None:
            plugins = self.__initialize_plugins()

            for plugin in plugins:
                plugin.register(container)

        def on_app_created(runtime_app: ApplicationRuntime) -> None:
            application.container = runtime_app.container

            runtime_app.on_startup(application.on_startup)
            runtime_app.on_shutdown(application.on_shutdown)

        runtime = self.__create_runtime(configure_container, on_app_created=on_app_created)
        return Application(runtime, application)


__all__ = [
    "Application",
    "ApplicationBase",
    "ApplicationBuilder",
    "ApplicationRuntime",
    "ConfigureContainer",
    "create_application",
]
