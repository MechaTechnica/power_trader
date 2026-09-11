"""Application builder and runtime discovery.

Applications are described by two pieces:

- a :class:`Plugin` (its wiring, via ``register``), and
- an :class:`ApplicationBase` (its lifecycle and run entry point).

Use :class:`ApplicationBuilder` to assemble and run them:

    app = (
        ApplicationBuilder(MyApplication)
        .with_plugin(MyPlugin)
        .build()
    )
    app.run()

The concrete runtime (``Container``, ``PluginRegistry``, ``Application``)
lives in ``power-core``; the framework discovers it via a package entry point
at build time, so applications depend only on ``power_trader_framework`` -
never on ``power_core`` directly.
"""

import importlib.metadata
from collections.abc import Awaitable, Callable, Iterable
from typing import Protocol, Self

from power_trader_framework.plugins import Plugin
from power_trader_framework.protocols.container import Container
from power_trader_framework.protocols.plugin import PluginRegistry, StrategyLifecycle
from power_trader_framework.protocols.strategy import Strategy
from power_trader_framework.settings import FrameworkSettings

#: Entry-point group/name that power-core registers to expose its runtime.
_RUNTIME_ENTRY_POINT_GROUP = "power_trader.runtime"
_RUNTIME_ENTRY_POINT_NAME = "create_application"


class ApplicationRuntime(Protocol):
    """Protocol for the runtime application object produced by power-core."""

    container: Container

    def on_startup(self, func: Callable[[], Awaitable[None]]) -> None: ...

    def on_shutdown(self, func: Callable[[], Awaitable[None]]) -> None: ...

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def run(self) -> None: ...


#: Callback applications implement to register their own dependencies.
ConfigureContainer = Callable[[Container, FrameworkSettings, PluginRegistry], None]

#: Callback applications implement to configure lifecycle hooks after the
#: ``Application`` has been created.
OnAppCreated = Callable[[ApplicationRuntime], None]


def _load_runtime_factory() -> Callable[..., ApplicationRuntime]:
    """Discover power-core's ``create_application`` via its entry point."""
    entry_points = importlib.metadata.entry_points()

    if hasattr(entry_points, "select"):
        matches = entry_points.select(
            group=_RUNTIME_ENTRY_POINT_GROUP, name=_RUNTIME_ENTRY_POINT_NAME
        )
    else:  # pragma: no cover - legacy entry_points() API
        matches = entry_points.get(_RUNTIME_ENTRY_POINT_GROUP, ())  # type: ignore[arg-type]

    for entry_point in matches:
        return entry_point.load()  # type: ignore[no-any-return]

    raise RuntimeError(
        "No framework runtime found. Install 'power-core' and ensure it "
        f"registers the '{_RUNTIME_ENTRY_POINT_GROUP}' entry point."
    )


def create_application(
    configure_container: ConfigureContainer,
    on_app_created: OnAppCreated | None = None,
) -> ApplicationRuntime:
    """Create an application using the discovered concrete runtime."""
    factory = _load_runtime_factory()
    return factory(configure_container, on_app_created)


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
        self._plugin_classes: list[type[Plugin]] = []

    def with_plugin(self, plugin_class: type[Plugin]) -> Self:
        """Add an application-wiring plugin class.

        Plugins are instantiated only during :meth:`build`, keeping builder
        construction side-effect free.
        """
        self._plugin_classes.append(plugin_class)
        return self

    def with_plugins(self, plugin_classes: Iterable[type[Plugin]]) -> Self:
        """Add application-wiring plugins from any iterable.

        This supports feature modules that expose a collection of plugins while
        preserving the supplied registration order.
        """
        self._plugin_classes.extend(plugin_classes)
        return self

    def build(self) -> Application:
        """Build the application: container, framework services, plugins, app."""
        application = self._application_class()
        plugins = [plugin_class() for plugin_class in self._plugin_classes]

        def configure_container(
            container: Container,
            _framework_settings: FrameworkSettings,
            registry: PluginRegistry,
        ) -> None:
            # Strategy composition: discover plugins, build instances, and bind
            # ``list[Strategy]`` so use cases can inject them.
            registry.discover()
            registry.build(container)
            container.register(list[Strategy], registry.get_all)
            # Application plugins' own registrations.
            for plugin in plugins:
                plugin.register(container)

        def on_app_created(runtime_app: ApplicationRuntime) -> None:
            application.container = runtime_app.container

            async def init_strategies() -> None:
                lifecycle = runtime_app.container.resolve(StrategyLifecycle)
                await lifecycle.initialize()

            async def cleanup_strategies() -> None:
                lifecycle = runtime_app.container.resolve(StrategyLifecycle)
                await lifecycle.cleanup()

            runtime_app.on_startup(init_strategies)
            runtime_app.on_startup(application.on_startup)
            runtime_app.on_shutdown(application.on_shutdown)
            runtime_app.on_shutdown(cleanup_strategies)

        runtime = create_application(configure_container, on_app_created=on_app_created)
        return Application(runtime, application)


__all__ = [
    "Application",
    "ApplicationBase",
    "ApplicationBuilder",
    "ApplicationRuntime",
    "create_application",
]
