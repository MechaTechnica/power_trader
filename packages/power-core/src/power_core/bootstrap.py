"""Application bootstrap utilities (composition root).

The *runtime* (power-core) owns creation of the concrete ``Container`` and the
framework capabilities (configuration, observability, health, events) that every
application needs. Applications never build these themselves.
"""

from typing import Any

from power_core.container import Container
from power_core.events import InMemoryEventBus
from power_core.health import HealthCheckRegistry, HealthService
from power_core.observability import (InMemoryAuditSink, InMemoryMetrics,
                                      OpenTelemetryTracer, StructuredLogger)
from power_core.observability import TerminalLogger as TerminalLoggerImpl
from power_core.runtime import Runtime
from power_framework.application import Runtime as RuntimeContract
from power_framework.events import Event, EventBus
from power_framework.health import \
    HealthCheckRegistry as HealthCheckRegistryContract
from power_framework.health import HealthService as HealthServiceContract
from power_framework.observability import (AuditSink, Logger, Metrics,
                                           TerminalLogger, Tracer)
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

    # Lifecycle: the runtime owns the application run loop (start -> run -> stop)
    # and its shutdown timeout is driven by the framework settings.
    runtime = Runtime(shutdown_timeout_seconds=settings.shutdown_timeout_seconds)
    container.register_instance(RuntimeContract, runtime)

    # structured logger is for logging the application state
    # you can use this to log to permanent storage (i.e cosmos db)
    logger = StructuredLogger(
        service=settings.service_name,
        environment=settings.environment.value,
        version=settings.service_version,
    )
    terminal_logger = TerminalLoggerImpl()
    container.register_instance(Logger, logger)
    container.register_instance(TerminalLogger, terminal_logger)
    container.register_instance(Metrics, InMemoryMetrics())
    # Tracing adapts to OpenTelemetry when installed, falling back to in-memory.
    container.register_instance(Tracer, OpenTelemetryTracer(service_name=settings.service_name))

    # Audit is a separate concern from operational logging: a dedicated sink
    # records immutable, compliance-grade audit events.
    container.register_instance(AuditSink, InMemoryAuditSink())

    # Health/readiness: applications register their own dependency checks.
    health_registry = HealthCheckRegistry()
    container.register_instance(HealthCheckRegistryContract, health_registry)
    container.register_instance(HealthServiceContract, HealthService(health_registry))

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
