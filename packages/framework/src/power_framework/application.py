from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from power_framework.plugins import (Plugin, _filter_entry_points,
                                     _get_entry_points)
from power_framework.protocols.container import Container
from power_framework.protocols.lifecycle import Lifecycle, LifecycleRegistry
from power_framework.settings import load_settings

PLUGIN_GROUP = "power.plugins"
CORE_NAME = "power-core"


class ApplicationBase:
    """Base class for an application's lifecycle and run entry point.

    Subclasses declare their dependencies as constructor arguments and override
    ``start``, ``stop``, and ``run``. The framework resolves and injects those
    dependencies automatically, so an application never needs to know that a DI
    container exists.

    The application is itself a :class:`Lifecycle` (the final stage to start and
    the first to stop); its own ``start``/``stop`` handle only application-level
    concerns.
    """

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    def run(self) -> None:
        return None


class Runtime(LifecycleRegistry):
    """Owns the ordered lifecycle of an application and its components.

    As a :class:`LifecycleRegistry`, it collects component types in the order
    plugins register them (infrastructure, domain services, extensions). ``start``
    resolves each type from the container and drives it in that order, then
    starts the application; ``stop`` reverses this. The application is always
    started last and stopped first.
    """

    def __init__(self, container: Container) -> None:
        self._container = container
        self._component_types: list[type[Any]] = []
        self._application: ApplicationBase | None = None

    def register(self, component_type: type[Any]) -> None:
        """Register a lifecycle component type to be resolved and driven."""
        self._component_types.append(component_type)

    def attach(self, application: ApplicationBase) -> None:
        """Attach the resolved application as the final lifecycle component."""
        self._application = application

    @property
    def application(self) -> ApplicationBase:
        application = self._application
        if application is None:
            raise RuntimeError("No application has been attached to the runtime.")
        return application

    async def start(self) -> None:
        """Start every component in dependency order, then the application."""
        for component_type in self._component_types:
            component = self._container.resolve(component_type)
            await component.start()
        await self.application.start()

    async def stop(self) -> None:
        """Stop the application first, then components in reverse order."""
        await self.application.stop()
        for component_type in reversed(self._component_types):
            component = self._container.resolve(component_type)
            await component.stop()

    def run(self) -> None:
        """Start the runtime, run the application, then stop the runtime."""
        asyncio.run(self.start())
        try:
            self.application.run()
        finally:
            asyncio.run(self.stop())


class ApplicationBootstrapper:
    """Assemble plugins, a runtime container, and an application instance.

    This class bridges the framework's plugin discovery with the concrete
    runtime (``power-core``) discovered via entry points. Plugins are registered
    into the container first (registering their lifecycle components), then the
    application is resolved and attached to the runtime.
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

    def bootstrap(self, application_class: type[ApplicationBase]) -> Runtime:
        """Build the container, register plugins, resolve and attach the app."""
        container = self._load_core_container()
        runtime = Runtime(container)
        for plugin in self._initialize_plugins():
            self._register_plugin_settings(container, plugin)
            plugin.register(container, runtime)
        container.register(application_class, application_class)
        runtime.attach(container.resolve(application_class))
        return runtime

    @staticmethod
    def _register_plugin_settings(container: Container, plugin: Plugin) -> None:
        """Load a plugin's declared settings and register them in the container.

        Configuration is a framework capability: plugins declare their settings
        type via ``Plugin.settings_class`` and the framework loads it (env +
        JSON file) before the plugin wires anything up, so applications never
        re-invent configuration loading.
        """
        settings_type = getattr(plugin, "settings_class", None)
        if settings_type is None:
            return
        container.register_instance(settings_type, load_settings(settings_type))


class ApplicationBuilder:
    """Fluent builder that assembles an application into a managed runtime."""

    def __init__(self, application_class: type[ApplicationBase]) -> None:
        self._application_class = application_class

    def build(self) -> Runtime:
        """Build the application and wrap it in a lifecycle-owning runtime."""
        app_bootstrapper = ApplicationBootstrapper()
        return app_bootstrapper.bootstrap(self._application_class)


__all__ = [
    "ApplicationBase",
    "ApplicationBuilder",
    "Runtime",
]
