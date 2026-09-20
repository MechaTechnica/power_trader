"""
Power Framework

Domain-agnostic application contracts for building applications: the DI
container protocol, lifecycle management, configuration, plugin discovery, and
application bootstrap. Trading-domain contracts live in ``power-market`` and
concrete runtime implementations live in ``power-core``.
"""

__version__ = "0.1.0"

from power_framework.application import (ApplicationBase, ApplicationBuilder,
                                         Runtime)
from power_framework.aspects import (AuditInterceptor, Interceptor,
                                     ObserveInterceptor, RetryInterceptor,
                                     audited, intercept, observed, retry)
from power_framework.events import (DomainEvent, Event, EventBus, EventHandler,
                                    InMemoryEventBus)
from power_framework.exceptions import (ApplicationError, ConfigurationError,
                                        DependencyError,
                                        DependencyValidationError, DomainError,
                                        FrameworkError, InfrastructureError,
                                        LifecycleError, PluginError,
                                        is_retryable)
from power_framework.health import (HealthCheck, HealthCheckRegistry,
                                    HealthReport, HealthService, HealthStatus,
                                    Status)
from power_framework.observability import (InMemoryMetrics, InMemoryTracer,
                                           Logger, Metrics, Span,
                                           StructuredLogger, Tracer,
                                           correlation_scope,
                                           current_correlation_id,
                                           current_trace_id)
from power_framework.plugins import Plugin
from power_framework.protocols.container import Container, Lifetime
from power_framework.protocols.lifecycle import Lifecycle, LifecycleRegistry
from power_framework.settings import (Environment, FrameworkSettings, LogLevel,
                                      Settings, TelemetrySettings,
                                      load_settings)
from power_framework.testing import (ApplicationTestHarness,
                                     TestApplicationBuilder)

__all__ = [
                                         "ApplicationBase",
                                         "ApplicationBuilder",
                                         "ApplicationError",
                                         "ApplicationTestHarness",
                                         "AuditInterceptor",
                                         "ConfigurationError",
                                         "Container",
                                         "DependencyError",
                                         "DependencyValidationError",
                                         "DomainError",
                                         "DomainEvent",
                                         "Environment",
                                         "Event",
                                         "EventBus",
                                         "EventHandler",
                                         "FrameworkError",
                                         "FrameworkSettings",
                                         "HealthCheck",
                                         "HealthCheckRegistry",
                                         "HealthReport",
                                         "HealthService",
                                         "HealthStatus",
                                         "InMemoryEventBus",
                                         "InMemoryMetrics",
                                         "InMemoryTracer",
                                         "InfrastructureError",
                                         "Interceptor",
                                         "Lifecycle",
                                         "LifecycleError",
                                         "LifecycleRegistry",
                                         "Lifetime",
                                         "LogLevel",
                                         "Logger",
                                         "Metrics",
                                         "ObserveInterceptor",
                                         "Plugin",
                                         "PluginError",
                                         "RetryInterceptor",
                                         "Runtime",
                                         "Settings",
                                         "Span",
                                         "Status",
                                         "StructuredLogger",
                                         "TelemetrySettings",
                                         "TestApplicationBuilder",
                                         "Tracer",
                                         "audited",
                                         "correlation_scope",
                                         "current_correlation_id",
                                         "current_trace_id",
                                         "intercept",
                                         "is_retryable",
                                         "load_settings",
                                         "observed",
                                         "retry",
]
