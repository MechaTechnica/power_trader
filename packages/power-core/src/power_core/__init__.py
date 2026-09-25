"""
Power Core

Runtime infrastructure for Power Trader applications.
Provides concrete implementations of the framework's abstractions:
Application lifecycle, DI container, event transports, health, and observability.

Applications should depend on ``power_framework`` (protocols,
``Plugin``, and ``ApplicationBuilder``), not on this package directly.
"""

__version__ = "0.1.0"

from power_core.bootstrap import create_container
from power_core.container import Container
from power_core.events import InMemoryEventBus, QueuedEventBus
from power_core.health import HealthCheckRegistry, HealthService
from power_core.observability import (InMemoryAuditSink, InMemoryMetrics,
                                      InMemoryTracer, OpenTelemetryTracer,
                                      StructuredLogger, TerminalLogger)
from power_core.runtime import Runtime
from power_framework.container import Lifetime

__all__ = [
    "Container",
    "HealthCheckRegistry",
    "HealthService",
    "InMemoryAuditSink",
    "InMemoryEventBus",
    "InMemoryMetrics",
    "InMemoryTracer",
    "Lifetime",
    "OpenTelemetryTracer",
    "QueuedEventBus",
    "Runtime",
    "StructuredLogger",
    "TerminalLogger",
    "create_container",
]
