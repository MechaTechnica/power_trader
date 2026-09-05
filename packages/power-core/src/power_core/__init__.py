"""
Power Core

Runtime infrastructure for Power Trader applications.
Provides concrete implementations of the framework's abstractions:
Application lifecycle, DI container, and plugin registry.

Applications should depend on ``power_trader_framework`` (protocols and
``ApplicationBase``), not on this package directly.
"""

__version__ = "0.1.0"

from power_core.application import Application
from power_core.bootstrap import create_application
from power_core.container import Container
from power_core.di_container import DIContainer, PluginRegistry
from power_core.exceptions import (ApplicationError, ConfigurationError,
                                   ConnectionError, DIError, PluginError)

__all__ = [
    "Application",
    "Container",
    "DIContainer",
    "PluginRegistry",
    "create_application",
    "ApplicationError",
    "ConfigurationError",
    "ConnectionError",
    "DIError",
    "PluginError",
]
