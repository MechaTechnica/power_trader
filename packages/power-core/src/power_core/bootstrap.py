"""Application bootstrap utilities (composition root).

The *runtime* (power-core) owns creation of the concrete ``Container``,
loading of ``CoreSettings``.
"""

from power_core.container import Container
from power_framework.application import (ApplicationBase,
                                                ApplicationModel)
from power_framework.settings import CoreSettings


def create_application(application_class: type[ApplicationBase]) -> ApplicationModel:
    """
    Create and configure an application.

    This is the runtime's entry point for building an application. It:

    1. Creates the ``Container`` (applications never do this themselves).
    2. Loads ``CoreSettings`` from the environment and registers it.
    3. Builds :class:`ApplicationModel`

    Returns:
        The built ApplicationModel
    """
    container = Container()
    container.register(CoreSettings, CoreSettings.load)
    application = application_class()

    return ApplicationModel(container=container, application=application)
