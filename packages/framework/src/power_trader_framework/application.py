"""Application base class and runtime discovery.

Applications subclass :class:`ApplicationBase` and override its lifecycle
hooks. The concrete runtime (``Container``, ``PluginRegistry``,
``Application``) lives in ``power-core``; the framework discovers it via a
package entry point at build time, so applications depend only on
``power_trader_framework`` - never on ``power_core`` directly.
"""

import asyncio
import importlib.metadata
from abc import ABC
from collections.abc import Awaitable, Callable
from typing import Protocol

from power_trader_framework.protocols.container import IContainer
from power_trader_framework.protocols.plugin import IPluginRegistry
from power_trader_framework.protocols.strategy import IStrategy
from power_trader_framework.settings import FrameworkSettings

#: Entry-point group/name that power-core registers to expose its runtime.
_RUNTIME_ENTRY_POINT_GROUP = "power_trader.runtime"
_RUNTIME_ENTRY_POINT_NAME = "create_application"


class IApplication(Protocol):
    """Protocol for the runtime application object produced by power-core."""

    container: IContainer

    def on_startup(self, func: Callable[[], Awaitable[None]]) -> None: ...

    def on_shutdown(self, func: Callable[[], Awaitable[None]]) -> None: ...

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def run(self) -> None: ...


#: Callback applications implement to register their own dependencies.
ConfigureContainer = Callable[[IContainer, FrameworkSettings, IPluginRegistry], None]

#: Callback applications implement to configure lifecycle hooks after the
#: ``Application`` has been created.
OnAppCreated = Callable[[IApplication], None]


def _load_runtime_factory() -> Callable[..., IApplication]:
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
) -> IApplication:
    """Create an application using the discovered concrete runtime."""
    factory = _load_runtime_factory()
    return factory(configure_container, on_app_created)


class ApplicationBase(ABC):
    """
    Base class every Power Trader application should subclass.

    Subclasses override the lifecycle hooks below; they never construct a
    ``Container``, ``PluginRegistry``, or ``Application`` directly - that
    responsibility belongs to the runtime discovered at build time.

    The framework automatically:

    - discovers strategy plugins, builds them, and wires up ``list[IStrategy]``,
    - initializes/cleans up strategies on startup/shutdown.

    Lifecycle hooks to override:

    - ``on_register(container)``: register application-specific adapters and
      use cases. Only ``container`` is passed; settings can be resolved via
      ``container.resolve(YourSettings)``.
    - ``on_startup()`` / ``on_shutdown()``: async lifecycle tasks. Only
      ``container.resolve(...)`` calls belong here.
    """

    def __init__(self) -> None:
        self._app: IApplication | None = None

    @property
    def app(self) -> IApplication:
        """The underlying ``Application``, available once built."""
        if self._app is None:
            raise RuntimeError(
                f"{type(self).__name__}.app accessed before the application "
                "was built; call build() or run() first."
            )
        return self._app

    @property
    def container(self) -> IContainer:
        """The DI container, available once the application has been built."""
        return self.app.container

    # ------------------------------------------------------------------
    # Lifecycle hooks - override in subclasses
    # ------------------------------------------------------------------
    def on_register(self, container: IContainer) -> None:
        """
        Register this application's dependencies against the container.

        Override to register application-specific adapters and use cases.
        The framework already registered settings, the output presenter, and
        the strategies. Only ``container`` is passed.
        """
        return None

    def on_app_created(self, application: IApplication) -> None:
        """
        Called once the ``Application`` instance exists, before it runs.

        Override for extra setup that needs the built ``Application``.
        Default implementation does nothing.
        """
        return None

    async def on_startup(self) -> None:
        """Override to perform startup tasks (``container.resolve`` only)."""
        return None

    async def on_shutdown(self) -> None:
        """Override to perform shutdown tasks (``container.resolve`` only)."""
        return None

    # ------------------------------------------------------------------
    # Framework wiring - not usually overridden
    # ------------------------------------------------------------------
    def build(self) -> IApplication:
        """Build the underlying ``Application`` via the discovered runtime.

        Idempotent: returns the already-built ``Application`` if called more
        than once.
        """
        if self._app is not None:
            return self._app

        def configure_container(
            container: IContainer,
            framework_settings: FrameworkSettings,
            plugin_registry: IPluginRegistry,
        ) -> None:
            self._register_framework_services(container, plugin_registry)
            self.on_register(container)

        def on_app_created(application: IApplication) -> None:
            application.on_startup(self._on_framework_startup)
            application.on_startup(self.on_startup)
            application.on_shutdown(self.on_shutdown)
            application.on_shutdown(self._on_framework_shutdown)
            self.on_app_created(application)

        self._app = create_application(configure_container, on_app_created=on_app_created)
        return self._app

    def _register_framework_services(
        self,
        container: IContainer,
        plugin_registry: IPluginRegistry,
    ) -> None:
        """Register framework-managed services before ``on_register`` runs."""
        plugin_registry.discover_strategies()
        plugin_registry.build_strategies(container)
        container.register(
            list[IStrategy],
            lambda registry: registry.get_all_strategies(),
            registry=plugin_registry,
        )

    async def _on_framework_startup(self) -> None:
        registry = self.container.resolve(IPluginRegistry)
        await registry.initialize_all()

    async def _on_framework_shutdown(self) -> None:
        registry = self.container.resolve(IPluginRegistry)
        await registry.cleanup_all()

    async def run_async(self) -> None:
        """Build (if needed) and run the application until shutdown."""
        app = self.build()
        await app.run()

    def run(self) -> None:
        """Build (if needed) and run the application until shutdown.

        Synchronous convenience wrapper around ``run_async()`` for CLI entry
        points; owns the asyncio event loop for the process.
        """
        asyncio.run(self.run_async())


# Re-export for convenience when importing from this module.
__all__ = ["ApplicationBase", "IApplication", "create_application"]
