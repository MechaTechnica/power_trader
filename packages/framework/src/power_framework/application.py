from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from power_framework.plugins import (Plugin, _filter_entry_points,
                                     _get_entry_points)
from power_framework.protocols.container import Container

PLUGIN_GROUP = "power.plugins"
CORE_NAME = "power-core"


@dataclass
class ApplicationModel:
    """The model for an application, containing the container and the constructed application."""

    container: Container
    application: ApplicationBase

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
            raise RuntimeError("Application has not been built; no application model available.")
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

    def _load_core_entry_point(self) -> Callable[[type[ApplicationBase]], ApplicationModel]:
        """Discover power-core's factory from the shared extension-point group."""
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

    def _load_core(self, application_class: type[ApplicationBase]) -> ApplicationModel:
        core_entry_point = self._load_core_entry_point()
        # The core runtime is responsible for creating the concrete
        # Application instance and wiring the ApplicationModel into it.
        return core_entry_point(application_class)

    def bootstrap(self, application_class: type[ApplicationBase]) -> ApplicationBase:
        """Build the runtime (in core), initialize plugins and return the created
        application instance.
        """
        application_model = self._load_core(application_class)
        application_model.application.application_model = application_model
        for plugin in self._initialize_plugins():
            plugin.register(application_model.container)
        return application_model.application


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
    "ApplicationModel",
]
