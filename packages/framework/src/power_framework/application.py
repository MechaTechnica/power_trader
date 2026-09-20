from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from power_framework.exceptions import (DependencyError, LifecycleError,
                                        PluginError)
from power_framework.plugins import (Plugin, _get_entry_points,
                                     _get_group_entry_points)
from power_framework.protocols.container import Container
from power_framework.protocols.lifecycle import LifecycleRegistry
from power_framework.settings import load_settings

PLUGIN_GROUP = "power.plugins"
CORE_GROUP = "power.core"


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

    @property
    def component_types(self) -> list[type[Any]]:
        """The lifecycle component types in start order (a copy)."""
        return list(self._component_types)

    def attach(self, application: ApplicationBase) -> None:
        """Attach the resolved application as the final lifecycle component."""
        self._application = application

    @property
    def application(self) -> ApplicationBase:
        application = self._application
        if application is None:
            raise LifecycleError("No application has been attached to the runtime.")
        return application

    async def start(self) -> None:
        """Start every component in dependency order, then the application."""
        for component_type in self._component_types:
            component = self._container.resolve(component_type)
            try:
                await component.start()
            except Exception as exc:
                raise LifecycleError(
                    f"Failed to start component "
                    f"'{getattr(component_type, '__name__', str(component_type))}': {exc}"
                ) from exc
        try:
            await self.application.start()
        except Exception as exc:
            raise LifecycleError(f"Failed to start application: {exc}") from exc

    async def stop(self) -> None:
        """Stop the application first, then components in reverse order."""
        try:
            await self.application.stop()
        except Exception as exc:
            raise LifecycleError(f"Failed to stop application: {exc}") from exc
        for component_type in reversed(self._component_types):
            component = self._container.resolve(component_type)
            try:
                await component.stop()
            except Exception as exc:
                raise LifecycleError(
                    f"Failed to stop component "
                    f"'{getattr(component_type, '__name__', str(component_type))}': {exc}"
                ) from exc

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

    def _load_core_entry_point(self) -> Callable[..., Container]:
        """Discover the installed runtime's container factory from its dedicated group.

        Core runtimes register under their own group, so any compatible runtime
        (``power-core`` today, a replacement tomorrow) is loaded without name
        matching. Exactly one core runtime is expected at any time.
        """
        entry_points = _get_entry_points()
        core_matches = _get_group_entry_points(entry_points, CORE_GROUP)

        if not core_matches:
            raise DependencyError(
                "No framework runtime found. Install a runtime such as "
                f"'power-core' and ensure it registers a '{CORE_GROUP}' entry point."
            )
        if len(core_matches) > 1:
            raise DependencyError(
                f"Multiple runtime entry points found in group '{CORE_GROUP}'. "
                "Only one core runtime may be installed."
            )

        return core_matches[0].load()  # type: ignore[no-any-return]

    def _load_plugins(self) -> set[type[Plugin]]:
        """Load and return every installed plugin class in the plugins group.

        Each loaded object must be a :class:`Plugin` subclass, and duplicate
        registrations (the same plugin class under multiple entry points) are
        returned only once.
        """
        entry_points = _get_entry_points()
        plugin_entries = _get_group_entry_points(entry_points, PLUGIN_GROUP)

        plugins: set[type[Plugin]] = set()
        for entry_point in sorted(plugin_entries, key=lambda candidate: candidate.name):
            plugin_class = entry_point.load()
            if not isinstance(plugin_class, type) or not issubclass(plugin_class, Plugin):
                raise PluginError(
                    f"Plugin entry point '{entry_point.name}' must expose a Plugin subclass"
                )
            plugins.add(plugin_class)
        return plugins

    def _initialize_plugins(self) -> list[Plugin]:
        """Instantiate one instance of every installed plugin."""
        return [plugin_class() for plugin_class in self._load_plugins()]

    def _load_core_container(
        self, framework_overrides: dict[Any, Any] | None = None
    ) -> Container:
        """Ask the runtime (power-core) for a configured container.

        ``framework_overrides`` replaces framework-supplied services (event bus,
        metrics, tracer, ...) *before* plugins wire, so plugins resolve the
        substitutes. This is the seam the test harness uses for captured
        telemetry/events.
        """
        core_entry_point = self._load_core_entry_point()
        if framework_overrides:
            return core_entry_point(framework_overrides)
        return core_entry_point()

    def assemble(
        self,
        application_class: type[ApplicationBase],
        *,
        overrides: list[tuple[Any, Any]] | None = None,
        framework_overrides: dict[Any, Any] | None = None,
    ) -> tuple[Container, Runtime]:
        """Run the bootstrap phases up to (but excluding) application construction.

        Bootstrap is explicitly phased so the container is never exposed to the
        application before wiring is complete:

        1. **Discover** plugins (and the runtime entry point).
        2. **Create the container** (the runtime registers the framework services:
           logging, configuration, telemetry, health, events).
        3. **Register framework overrides** — substituted *before* plugins wire,
           so plugins resolve the fakes (captured telemetry/events).
        4. **Register modules** — load each plugin's settings, then let it register
           its application services and lifecycle components.
        5. **Register the application** as the composition root.
        6. **Apply module overrides** — substitutes for adapters the plugins
           themselves registered.

        The caller is then responsible for validating the dependency graph and
        constructing the application. This keeps module wiring and application
        construction strictly ordered and independently testable.
        """
        container = self._load_core_container(framework_overrides)
        runtime = Runtime(container)

        for plugin in self._initialize_plugins():
            self._register_plugin_settings(container, plugin)
            plugin.register(container, runtime)

        container.register(application_class, application_class)

        for interface, instance in overrides or []:
            container.override(interface, instance)

        return container, runtime

    def validate(
        self,
        application_class: type[ApplicationBase],
        *,
        overrides: list[tuple[Any, Any]] | None = None,
        framework_overrides: dict[Any, Any] | None = None,
    ) -> None:
        """Validate the application's dependency graph before construction.

        Raises:
            DependencyValidationError: If the application or any lifecycle
                component has an unsatisfiable dependency, with a tree report.
        """
        container, runtime = self.assemble(
            application_class,
            overrides=overrides,
            framework_overrides=framework_overrides,
        )
        roots = [application_class, *runtime.component_types]
        container.validate(*roots)

    def bootstrap(
        self,
        application_class: type[ApplicationBase],
        *,
        validate: bool = False,
        overrides: list[tuple[Any, Any]] | None = None,
        framework_overrides: dict[Any, Any] | None = None,
    ) -> Runtime:
        """Assemble the application and attach it to the runtime.

        Args:
            application_class: The application type to construct and run.
            validate: When ``True``, validate the dependency graph after wiring
                and before construction (fail fast with a tree report).
            overrides: Optional ``(interface, instance)`` pairs applied after
                module wiring (the test seam for replacing adapters with fakes).
            framework_overrides: Optional ``interface -> instance`` map applied
                before module wiring (substitutes the framework's event bus,
                metrics, tracer, etc. so plugins resolve the fakes).
        """
        container, runtime = self.assemble(
            application_class,
            overrides=overrides,
            framework_overrides=framework_overrides,
        )
        if validate:
            roots = [application_class, *runtime.component_types]
            container.validate(*roots)
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
    """Fluent builder that assembles an application into a managed runtime.

    ``ApplicationBuilder(MyApplication).build()`` works out of the box: the
    runtime supplies sensible defaults for logging, configuration, telemetry,
    health, lifecycle, and error handling, so teams only override what they need.
    """

    def __init__(self, application_class: type[ApplicationBase], *, validate: bool = False) -> None:
        self._application_class = application_class
        self._validate = validate

    def validate(self) -> ApplicationBuilder:
        """Validate the dependency graph, returning ``self`` for chaining.

        Raises:
            DependencyValidationError: If the graph is incomplete, with a tree
                showing each dependency as ``✓`` or ``✗ missing``.
        """
        ApplicationBootstrapper().validate(self._application_class)
        return self

    def build(self) -> Runtime:
        """Build the application and wrap it in a lifecycle-owning runtime."""
        app_bootstrapper = ApplicationBootstrapper()
        return app_bootstrapper.bootstrap(
            self._application_class, validate=self._validate
        )


__all__ = [
    "ApplicationBase",
    "ApplicationBuilder",
    "Runtime",
]
