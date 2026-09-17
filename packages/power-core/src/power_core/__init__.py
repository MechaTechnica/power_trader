"""
Power Core

Runtime infrastructure for Power Trader applications.
Provides concrete implementations of the framework's abstractions:
Application lifecycle and DI container.

Applications should depend on ``power_trader_framework`` (protocols,
``Plugin``, and ``ApplicationBuilder``), not on this package directly.
"""

__version__ = "0.1.0"

from power_core.bootstrap import create_application
from power_core.container import Container
from power_core.exceptions import (ApplicationError, ConfigurationError,
                                   ConnectionError, DIError, PluginError)

__all__ = [
                                   "ApplicationError",
                                   "ConfigurationError",
                                   "ConnectionError",
                                   "Container",
                                   "DIError",
                                   "PluginError",
                                   "create_application",
]
