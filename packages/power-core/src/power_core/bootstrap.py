"""Application bootstrap utilities (composition root).

The *runtime* (power-core) owns creation of the concrete ``Container`` and the
framework capabilities (configuration, observability, health, events) that every
application needs. Applications never build these themselves.
"""

from typing import Any

from power_core.container import Container
from power_framework.events import Event, EventBus, InMemoryEventBus
from power_framework.health import HealthCheckRegistry, HealthService
from power_framework.observability import (
    InMemoryMetrics,
    InMemoryTracer,
    Logger,
    Metrics,
    StructuredLogger,
    Tracer,
)
from power_framework.settings import FrameworkSettings, load_settings


def create_container(
    overrides: dict[Any, Any] | None = None,
) -> Container:
    """Create and configure the runtime container.

    This is the runtime's entry point for building an application. It:

    1. Creates the ``Container`` (applications never do this themselves).
    2. Loads ``FrameworkSettings`` and registers it.
    3. Builds and registers the shared observability capability (structured
       ``Logger``, ``Metrics``, ``Tracer``) with automatic context injection.
    4. Builds and registers the health/readiness capability.
    5. Builds and registers the shared event bus (with error isolation).
    6. Applies any ``overrides`` (interface -> instance) supplied by the caller.

    ``overrides`` is the framework's test seam: the caller substitutes the
    framework's *defaults* (an in-memory event bus, a fake tracer, ...) before
    any plugin wires, so plugins resolve the substitutes rather than the real
    defaults.

    The framework then registers plugins into this container and resolves the
    application from it, injecting the application's constructor dependencies.

    Args:
        overrides: Optional ``interface -> instance`` map applied over the
            framework's sensible defaults.

    Returns:
        The configured runtime container.
    """
    if overrides is None:
        overrides = {}

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

    # Events: one shared bus; handler failures are logged, not raised, so a
    # failing subscriber never takes down the whole pipeline.
    async def on_event_error(event: Event, error: Exception) -> None:
        logger.error(
            "event_handler_failed",
            event_type=type(event).__name__,
            error=str(error),
        )

    container.register_instance(EventBus, InMemoryEventBus(on_error=on_event_error))

    for interface, instance in overrides.items():
        container.override(interface, instance)

    return container
