"""Application bootstrap utilities (composition root).

The *runtime* (power-core) owns creation of the concrete ``Container``,
loading of ``CoreSettings``.
Applications never construct these themselves; they provide a
``configure_container`` callback (typed against the framework's ``Container``
protocol) that registers their own
settings/adapters/use-cases.

This function is exposed to the framework through the shared ``power_trader.plugins``
entry point, so applications depend only on ``power_trader_framework`` and
never import ``power_core`` directly.
"""

from power_core.container import Container
from power_trader_framework.application import (ApplicationModel,
                                                ConfigureContainer,
                                                OnAppCreated)
from power_trader_framework.settings import CoreSettings


def create_application(
    configure_container: ConfigureContainer,
    on_app_created: OnAppCreated | None = None,
) -> ApplicationModel:
    """
    Create and configure an application.

    This is the runtime's entry point for building an application. It:

    1. Creates the ``Container`` (applications never do this themselves).
    2. Loads ``CoreSettings`` from the environment and registers it.
    3. Invokes ``configure_container`` so the application can register its
       own settings, adapters, and use cases against the container.
    5. Builds an :class:`ApplicationModel` around the container and invokes
       ``on_app_created`` if provided.

    Args:
        configure_container: Callback invoked with the ``container`` so the
            application can register its own dependencies. Applications must
            not construct their own ``Container``. ``CoreSettings`` is already
            registered and can be resolved via ``container.resolve(CoreSettings)``.
        on_app_created: Optional callback invoked with the built model so the
            caller can read its ``container``.

    Returns:
        The built ApplicationModel holding the resolved container.
    """
    container = Container()

    core_settings = CoreSettings.load()
    container.register_instance(CoreSettings, core_settings)

    configure_container(container)

    model = ApplicationModel(container)

    if on_app_created:
        # Synchronous by design: it should only read the model, not run async work.
        on_app_created(model)

    return model
