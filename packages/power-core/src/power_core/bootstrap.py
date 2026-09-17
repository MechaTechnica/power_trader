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


def create_application() -> ApplicationModel:
    """
    Create and configure an application.

    This is the runtime's entry point for building an application. It:

    1. Creates the ``Container`` (applications never do this themselves).
    2. Loads ``CoreSettings`` from the environment and registers it.
    3. Builds an :class:`ApplicationModel` around the container and invokes
       ``on_app_created`` if provided.

    Returns:
        The built ApplicationModel holding the resolved container.
    """
    container = Container()

    container.register(CoreSettings, CoreSettings.load)

    return ApplicationModel(container)
