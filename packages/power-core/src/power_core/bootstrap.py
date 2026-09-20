"""Application bootstrap utilities (composition root).

The *runtime* (power-core) owns creation of the concrete ``Container`` and
loading of ``CoreSettings``.
"""

from power_core.container import Container
from power_framework.settings import CoreSettings


def create_container() -> Container:
    """Create and configure the runtime container.

    This is the runtime's entry point for building an application. It:

    1. Creates the ``Container`` (applications never do this themselves).
    2. Loads ``CoreSettings`` and registers it.

    The framework then registers plugins into this container and resolves the
    application from it, injecting the application's constructor dependencies.

    Returns:
        The configured runtime container.
    """
    container = Container()
    container.register(CoreSettings, CoreSettings)
    return container
