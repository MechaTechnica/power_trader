"""Application bootstrap utilities (composition root).

The *runtime* (power-core) owns creation of the concrete ``Container``,
loading of ``FrameworkSettings``, and construction of the ``PluginRegistry``.
Applications never construct these themselves; they provide a
``configure_container`` callback (typed against the framework's ``Container``
and ``PluginRegistry`` protocols) that registers their own
settings/adapters/use-cases.

This function is exposed to the framework through the ``power_trader.runtime``
entry point, so applications depend only on ``power_trader_framework`` and
never import ``power_core`` directly.
"""

from collections.abc import Callable

from power_core.application import Application
from power_core.container import Container
from power_core.di_container import PluginRegistry
from power_trader_framework.protocols.container import \
    Container as ContainerProtocol
from power_trader_framework.protocols.plugin import \
    PluginRegistry as PluginRegistryProtocol
from power_trader_framework.settings import FrameworkSettings

#: Callback applications implement to register their own dependencies.
ConfigureContainer = Callable[
    [ContainerProtocol, FrameworkSettings, PluginRegistryProtocol], None
]

#: Callback applications implement to configure lifecycle hooks after the
#: ``Application`` has been created. Synchronous - it should only *register*
#: hooks (e.g. via ``app.on_startup(...)``), not execute async work itself.
OnAppCreated = Callable[[Application], None]


def create_application(
    configure_container: ConfigureContainer,
    on_app_created: OnAppCreated | None = None,
) -> Application:
    """
    Create and configure an application.

    This is the runtime's entry point for building an application. It:

    1. Creates the ``Container`` (applications never do this themselves).
    2. Loads ``FrameworkSettings`` from the environment and registers it.
    3. Creates the ``PluginRegistry`` and registers it under both its
       concrete type and the ``PluginRegistry`` protocol.
    4. Invokes ``configure_container`` so the application can register its
       own settings, adapters, and use cases against the container.
    5. Creates the ``Application`` instance and invokes ``on_app_created``
       if provided, so the application can register startup/shutdown hooks.

    Args:
        configure_container: Callback invoked with ``(container,
            framework_settings, plugin_registry)`` so the application can
            register its own dependencies. Applications must not construct
            their own ``Container``.
        on_app_created: Optional callback to configure the app after
            creation.

    Returns:
        Configured Application instance.
    """
    container = Container()

    framework_settings = FrameworkSettings.load()
    container.register_instance(FrameworkSettings, framework_settings)

    plugin_registry = PluginRegistry()
    container.register_instance(PluginRegistryProtocol, plugin_registry)
    container.register_instance(PluginRegistry, plugin_registry)

    configure_container(container, framework_settings, plugin_registry)

    app = Application(container)

    if on_app_created:
        # Synchronous by design: it should only *register* hooks, not run them.
        on_app_created(app)

    return app
