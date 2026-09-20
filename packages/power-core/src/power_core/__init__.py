"""
Power Core

Runtime infrastructure for Power Trader applications.
Provides concrete implementations of the framework's abstractions:
Application lifecycle and DI container.

Applications should depend on ``power_framework`` (protocols,
``Plugin``, and ``ApplicationBuilder``), not on this package directly.
"""

__version__ = "0.1.0"

from power_core.bootstrap import create_container
from power_core.container import Container
from power_core.exceptions import (
    ApplicationError,
    ConfigurationError,
    ConnectionError,
    DependencyError,
    DependencyValidationError,
    DIError,
    DomainError,
    FrameworkError,
    InfrastructureError,
    LifecycleError,
    PluginError,
    StrategyError,
)
from power_framework.protocols.container import Lifetime

__all__ = [
    "ApplicationError",
    "ConfigurationError",
    "ConnectionError",
    "Container",
    "DIError",
    "DependencyError",
    "DependencyValidationError",
    "DomainError",
    "FrameworkError",
    "InfrastructureError",
    "LifecycleError",
    "Lifetime",
    "PluginError",
    "StrategyError",
    "create_container",
]
