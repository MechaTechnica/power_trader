from collections.abc import Awaitable, Callable
from typing import Any, Protocol, Self

from power_framework.container import Container
from power_framework.exceptions import FrameworkError
from power_framework.plugins import (Plugin, _get_entry_points,
                                     _get_group_entry_points)
from power_framework.settings import FrameworkSettings, load_settings

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

    Lifecycle methods may be implemented either synchronously or as
    coroutines. The runtime detects which style each method uses and drives
    the application accordingly, so an application that does not need asyncio
    can remain fully synchronous while async applications are unaffected.
    """

    def start(self) -> Awaitable[None] | None:
        """Start the application. May be implemented synchronously or async."""
        return None

    def stop(self) -> Awaitable[None] | None:
        """Stop the application. May be implemented synchronously or async."""
        return None

    def run(self) -> Awaitable[None] | None:
        """Run the application to completion. May be synchronous or async."""
        return None


# The async hooks below intentionally override the synchronous
# ``ApplicationBase`` hooks. This is the single place the framework bridges the
# two styles so that async applications can use ``async def`` without needing
# any suppression of their own.
# pylint: disable=invalid-overridden-method
class AsyncApplicationBase(ApplicationBase):
    """Base class for applications whose lifecycle is asynchronous.

    Overrides the lifecycle hooks as coroutines so subclasses implement
    ``start``, ``run``, and ``stop`` with ``async def`` methods. Overriding an
    async hook with an async coroutine satisfies static analysers without any
    per-application suppressions. The runtime detects the coroutine style and
    drives the application on the event loop it owns.

    Applications that are entirely synchronous should subclass
    :class:`ApplicationBase` directly instead; the two styles may not be mixed
    within a single application's hooks intentionally.
    """

    async def start(self) -> None:
        """Start the application."""
        return None

    async def stop(self) -> None:
        """Stop the application."""
        return None

    async def run(self) -> None:
        """Run the application to completion."""
        return None


class Runtime(Protocol):
    """Contract for the application run-loop owner.

    The framework knows only this interface; the concrete ``Runtime``
    implementation (which owns the event loop and drives ``start`` -> ``run`` ->
    ``stop``) lives in ``power_core.runtime`` and is registered in the container
    by the runtime's ``create_container`` entry point.
    """

    @property
    def application(self) -> ApplicationBase:
        """The attached application."""

    def attach(self, application: ApplicationBase) -> None:
        """Attach the resolved application."""

    async def start(self) -> None:
        """Start the application."""

    async def stop(self) -> None:
        """Stop the application, optionally bounded by the shutdown timeout."""

    def run(self) -> None:
        """Run the application to completion, owning the event loop."""

    async def run_async(self) -> None:
        """Run the application on the ambient event loop."""


class ApplicationBootstrapper:
    """Assemble plugins, a runtime container, and an application instance.

    This class bridges the framework's plugin discovery with the concrete
    runtime (``power-core``) discovered via entry points. Plugins are registered
    into the container first, then the application is resolved and attached
    to the runtime.

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
            raise FrameworkError(
                "No framework runtime found. Install a runtime such as "
                f"'power-core' and ensure it registers a '{CORE_GROUP}' entry point."
            )
        if len(core_matches) > 1:
            raise FrameworkError(
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
                raise FrameworkError(
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
        runtime = container.resolve(Runtime)

        # Effective allowlist: explicit builder allowlist wins; otherwise fall
        # back to the configured allowlist (discovery != authorization).
        allowlist = enabled_plugins
        if allowlist is None and settings.enabled_plugins:
            allowlist = set(settings.enabled_plugins)

        for plugin in self._initialize_plugins(allowlist):
            self._register_plugin_settings(container, plugin)
            plugin.register(container)

        # application itself is singleton
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
            FrameworkError: If the application has an unsatisfiable dependency,
                with a tree report.
        """
        container, _ = self.assemble(
            application_class,
            overrides=overrides,
            framework_overrides=framework_overrides,
            enabled_plugins=enabled_plugins,
        )
        roots = [application_class]
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
            roots = [application_class]
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

    def with_plugins(self, *plugin_classes: type[Plugin]) -> Self:
        """Authorize only the given plugin classes (by name) to load.

        This is the explicit allowlist that separates plugin *discovery* from
        plugin *authorization*: installed packages are discovered, but only the
        named plugins are loaded and executed.
        """
        self._enabled_plugins = {_plugin_name(p) for p in plugin_classes}
        return self

    def validate(self) -> Self:
        """Validate the dependency graph, returning ``self`` for chaining.

        Raises:
            FrameworkError: If the graph is incomplete, with a tree showing each
                dependency as ``✓`` or ``✗ missing``.
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
    "AsyncApplicationBase",
    "Runtime",
]
