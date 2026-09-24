from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from power_framework.exceptions import DependencyError, LifecycleError, PluginError
from power_framework.plugins import Plugin, _get_entry_points, _get_group_entry_points
from power_framework.protocols.lifecycle import LifecycleRegistry
from power_framework.settings import FrameworkSettings, load_settings

if TYPE_CHECKING:
    from collections.abc import Callable

    from power_framework.protocols.container import Container

PLUGIN_GROUP = "power.plugins"
CORE_GROUP = "power.core"


def _plugin_name(plugin_class: type[Plugin]) -> str:
    """Return a plugin's effective name (metadata first, then legacy ``name``)."""
    meta_name = plugin_class.metadata.name
    if meta_name != "unnamed":
        return meta_name
    return getattr(plugin_class, "name", None) or "unnamed"


class ApplicationBase:
    """Base class for an application's lifecycle and run entry point.

    Subclasses declare their dependencies as constructor arguments and override
    ``start``, ``stop``, and ``run``. The framework resolves and injects those
    dependencies automatically, so an application never needs to know that a DI
    container exists.

    The application is itself a :class:`Lifecycle` (the final stage to start and
    the first to stop); its own ``start``/``stop`` handle only application-level
    concerns. ``run`` is the application's main loop and is awaited on the same
    event loop as the rest of the runtime.
    """

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def run(self) -> None:
        return None


class Runtime(LifecycleRegistry):
    """Owns the ordered lifecycle of an application and its components.

    As a :class:`LifecycleRegistry`, it collects component types in the order
    plugins register them (infrastructure, domain services, extensions). ``start``
    resolves each type from the container and drives it in that *registration*
    order, then starts the application; ``stop`` reverses this. The application
    is always started last and stopped first.

    ``run`` drives the whole lifecycle on a **single** event loop: it awaits
    ``start``, then the application's ``run``, then ``stop``. This avoids the
    bug of binding event-loop-owned resources (clients, connections) to one loop
    and tearing them down on another.
    """

    def __init__(
        self,
        container: Container,
        *,
        shutdown_timeout_seconds: float | None = None,
    ) -> None:
        self._container = container
        self._component_types: list[type[Any]] = []
        self._application: ApplicationBase | None = None
        self._shutdown_timeout_seconds = shutdown_timeout_seconds

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
        """Start every component in registration order, then the application.

        Startup is fail-fast: the first component that fails aborts startup.
        """
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
        """Stop the application first, then components in reverse order.

        Shutdown is *resilient*: every component is given a chance to stop even
        if an earlier one fails. Failures are collected and reported together
        (as a single :class:`LifecycleError`) rather than aborting the remaining
        cleanup. Each component's stop is bounded by ``shutdown_timeout_seconds``
        when configured.
        """
        errors: list[Exception] = []

        try:
            await self._stop_component(self.application, "application")
        except Exception as exc:
            errors.append(exc)

        for component_type in reversed(self._component_types):
            component = self._container.resolve(component_type)
            name = getattr(component_type, "__name__", str(component_type))
            try:
                await self._stop_component(component, name)
            except Exception as exc:
                errors.append(exc)

        if errors:
            detail = "; ".join(str(e) for e in errors)
            raise LifecycleError(f"Shutdown completed with {len(errors)} failure(s): {detail}")

    async def _stop_component(self, component: Any, name: str) -> None:
        """Stop ``component``, optionally bounded by the shutdown timeout."""
        if self._shutdown_timeout_seconds is None:
            await component.stop()
            return
        try:
            await asyncio.wait_for(
                component.stop(),
                timeout=self._shutdown_timeout_seconds,
            )
        except TimeoutError as exc:
            raise LifecycleError(
                f"Timed out stopping '{name}' after "
                f"{self._shutdown_timeout_seconds}s"
            ) from exc

    def run(self) -> None:
        """Run the application to completion, owning the event loop.

        This is the synchronous public entry point for application developers:
        the framework owns the async execution model (a single event loop driving
        ``start`` → ``run`` → ``stop``), so callers never need to know about
        ``asyncio``.
        """
        asyncio.run(self.run_async())

    async def run_async(self) -> None:
        """Run the application on the ambient event loop.

        Use this when the framework is *embedded* inside an already-running event
        loop (another async application, a notebook, or an async test runner),
        where creating a second loop via :meth:`run` would be incorrect.
        """
        await self.start()
        try:
            await self.application.run()
        finally:
            await self.stop()


class ApplicationBootstrapper:
    """Assemble plugins, a runtime container, and an application instance.

    This class bridges the framework's plugin discovery with the concrete
    runtime (``power-core``) discovered via entry points. Plugins are registered
    into the container first (registering their lifecycle components), then the
    application is resolved and attached to the runtime.

    Plugin discovery is separated from plugin *authorization*: discovery finds
    every installed plugin, while an explicit allowlist (``enabled_plugins``)
    decides which discovered plugins are actually loaded and executed.
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

    def _load_plugins(self, allowlist: set[str] | None = None) -> set[type[Plugin]]:
        """Load and return every *authorized* plugin class in the plugins group.

        Discovery finds every installed plugin; the optional ``allowlist`` (a set
        of plugin names or entry-point names) restricts which discovered plugins
        are authorized to load and execute. When ``allowlist`` is ``None``, all
        discovered plugins are authorized (the permissive default).

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
            if allowlist is not None:
                name = _plugin_name(plugin_class)
                if name not in allowlist and entry_point.name not in allowlist:
                    continue
            plugins.add(plugin_class)
        return plugins

    def _initialize_plugins(self, allowlist: set[str] | None = None) -> list[Plugin]:
        """Instantiate one instance of every authorized plugin."""
        return [plugin_class() for plugin_class in self._load_plugins(allowlist)]

    def _load_core_container(self, framework_overrides: dict[Any, Any] | None = None) -> Container:
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
        enabled_plugins: set[str] | None = None,
    ) -> tuple[Container, Runtime]:
        """Run the bootstrap phases up to (but excluding) application construction.

        Bootstrap is explicitly phased so the container is never exposed to the
        application before wiring is complete:

        1. **Discover** plugins (and the runtime entry point).
        2. **Authorize** plugins against the ``enabled_plugins`` allowlist.
        3. **Create the container** (the runtime registers the framework services:
           logging, configuration, telemetry, health, events).
        4. **Register framework overrides** — substituted *before* plugins wire.
        5. **Register modules** — load each plugin's settings, then let it register
           its application services and lifecycle components.
        6. **Register the application** as the composition root.
        7. **Apply module overrides** — substitutes for adapters the plugins
           themselves registered.
        """
        container = self._load_core_container(framework_overrides)
        settings = container.resolve(FrameworkSettings)
        runtime = Runtime(
            container,
            shutdown_timeout_seconds=settings.shutdown_timeout_seconds,
        )

        # Effective allowlist: explicit builder allowlist wins; otherwise fall
        # back to the configured allowlist (discovery != authorization).
        allowlist = enabled_plugins
        if allowlist is None and settings.enabled_plugins:
            allowlist = set(settings.enabled_plugins)

        for plugin in self._initialize_plugins(allowlist):
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
        enabled_plugins: set[str] | None = None,
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
            enabled_plugins=enabled_plugins,
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
        enabled_plugins: set[str] | None = None,
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
            enabled_plugins: Optional allowlist of plugin names to authorize.
        """
        container, runtime = self.assemble(
            application_class,
            overrides=overrides,
            framework_overrides=framework_overrides,
            enabled_plugins=enabled_plugins,
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

    Plugin authorization is explicit: use :meth:`with_plugins` to restrict which
    discovered plugins are loaded, or configure ``FrameworkSettings.enabled_plugins``.
    """

    def __init__(self, application_class: type[ApplicationBase], *, validate: bool = False) -> None:
        self._application_class = application_class
        self._validate = validate
        self._enabled_plugins: set[str] | None = None

    def with_plugins(self, *plugin_classes: type[Plugin]) -> ApplicationBuilder:
        """Authorize only the given plugin classes (by name) to load.

        This is the explicit allowlist that separates plugin *discovery* from
        plugin *authorization*: installed packages are discovered, but only the
        named plugins are loaded and executed.
        """
        self._enabled_plugins = {_plugin_name(p) for p in plugin_classes}
        return self

    def validate(self) -> ApplicationBuilder:
        """Validate the dependency graph, returning ``self`` for chaining.

        Raises:
            DependencyValidationError: If the graph is incomplete, with a tree
                showing each dependency as ``✓`` or ``✗ missing``.
        """
        ApplicationBootstrapper().validate(
            self._application_class,
            enabled_plugins=self._enabled_plugins,
        )
        return self

    def build(self) -> Runtime:
        """Build the application and wrap it in a lifecycle-owning runtime."""
        app_bootstrapper = ApplicationBootstrapper()
        return app_bootstrapper.bootstrap(
            self._application_class,
            validate=self._validate,
            enabled_plugins=self._enabled_plugins,
        )


__all__ = [
    "ApplicationBase",
    "ApplicationBuilder",
    "Runtime",
]
