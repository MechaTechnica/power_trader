from __future__ import annotations

from collections.abc import Callable

from power_framework.plugins import (Plugin, _filter_entry_points,
                                     _get_entry_points)
from power_framework.protocols.container import Container

PLUGIN_GROUP = "power.plugins"
CORE_NAME = "power-core"


class ApplicationBase:
    """Base class for an application's lifecycle and run entry point.

    Subclasses declare their dependencies as constructor arguments and override
    ``on_startup``, ``on_shutdown``, and ``run``. The framework resolves and
    injects those dependencies automatically, so an application never needs to
    know that a DI container exists.
    """

    async def on_startup(self) -> None:
        return None

    async def on_shutdown(self) -> None:
        return None

    def run(self) -> None:
        return None


class ApplicationBootstrapper:
    """Assemble plugins, a runtime container, and an application instance.

    This class bridges the framework's plugin discovery with the concrete
    runtime (``power-core``) discovered via entry points. Plugins are registered
    into the container first, then the application is resolved from the
    container so its constructor dependencies are injected.
    """

    def _load_core_entry_point(self) -> Callable[[], Container]:
        """Discover power-core's container factory from the shared extension-point group."""
        entry_points = _get_entry_points()
        core_matches = _filter_entry_points(entry_points, PLUGIN_GROUP, lambda name: name == CORE_NAME)

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

    def _load_plugins(self) -> set[type[Plugin]]:
        """Load and return every installed plugin class in the shared group.

        The ``core`` entry point is the runtime factory rather than a plugin, so it
        is excluded by name. Each loaded object must be a :class:`Plugin` subclass,
        and duplicate registrations (the same plugin class under multiple entry
        points) are returned only once.
        """
        entry_points = _get_entry_points()
        plugin_entries = _filter_entry_points(entry_points, PLUGIN_GROUP, lambda name: name != CORE_NAME)

        plugins: set[type[Plugin]] = set()
        for entry_point in sorted(plugin_entries, key=lambda candidate: candidate.name):
            plugin_class = entry_point.load()
            if not isinstance(plugin_class, type) or not issubclass(plugin_class, Plugin):
                raise TypeError(
                    f"Plugin entry point '{entry_point.name}' must expose a Plugin subclass"
                )
            plugins.add(plugin_class)
        return plugins

    def _initialize_plugins(self) -> list[Plugin]:
        """Instantiate one instance of every installed plugin."""
        return [plugin_class() for plugin_class in self._load_plugins()]

    def _load_core_container(self) -> Container:
        """Ask the runtime (power-core) for a configured container."""
        core_entry_point = self._load_core_entry_point()
        return core_entry_point()

    def bootstrap(self, application_class: type[ApplicationBase]) -> ApplicationBase:
        """Build the container, register plugins, then resolve the application.

        Plugins are registered before the application is resolved so the
        application's constructor dependencies are available to the container.
        """
        container = self._load_core_container()
        for plugin in self._initialize_plugins():
            plugin.register(container)
        container.register(application_class, application_class)
        return container.resolve(application_class)


class ApplicationBuilder:
    """Fluent builder that assembles an application from plugins and an app."""

    def __init__(self, application_class: type[ApplicationBase]) -> None:
        self._application_class = application_class

    def build(self) -> ApplicationBase:
        """Build the application: container, framework services, plugins, app."""
        app_bootstrapper = ApplicationBootstrapper()
        return app_bootstrapper.bootstrap(self._application_class)


__all__ = [
    "ApplicationBase",
    "ApplicationBuilder",
]
