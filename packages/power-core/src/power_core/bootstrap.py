"""Application bootstrap utilities (composition root).

The *runtime* (power-core) owns creation of the concrete ``Container`` and the
framework capabilities (configuration, observability, health) that every
application needs. Applications never build these themselves.
"""

from power_core.container import Container
from power_framework.health import HealthCheckRegistry, HealthService
from power_framework.observability import (InMemoryMetrics, InMemoryTracer,
                                           Logger, Metrics, StructuredLogger,
                                           Tracer)
from power_framework.settings import FrameworkSettings, load_settings


def create_container() -> Container:
    """Create and configure the runtime container.

    This is the runtime's entry point for building an application. It:

    1. Creates the ``Container`` (applications never do this themselves).
    2. Loads ``FrameworkSettings`` and registers it.
    3. Builds and registers the shared observability capability (structured
       ``Logger``, ``Metrics``, ``Tracer``) with automatic context injection.
    4. Builds and registers the health/readiness capability.

    The framework then registers plugins into this container and resolves the
    application from it, injecting the application's constructor dependencies.

    Returns:
        The configured runtime container.
    """
    container = Container()

    settings = load_settings(FrameworkSettings)
    container.register_instance(FrameworkSettings, settings)

    # Observability: one shared stack, sourced from framework settings.
    logger = StructuredLogger(
        service=settings.service_name,
        environment=settings.environment.value,
        version=settings.service_version,
    )
    container.register_instance(Logger, logger)
    container.register_instance(Metrics, InMemoryMetrics())
    container.register_instance(Tracer, InMemoryTracer())

    # Health/readiness: applications register their own dependency checks.
    health_registry = HealthCheckRegistry()
    container.register_instance(HealthCheckRegistry, health_registry)
    container.register_instance(HealthService, HealthService(health_registry))

    return container
