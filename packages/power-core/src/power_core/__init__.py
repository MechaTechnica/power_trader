"""
Power Core

Runtime infrastructure for Power Trader applications.
Provides Application lifecycle, DI container, and plugin system.
"""

__version__ = "0.1.0"

from power_core.application import Application
from power_core.di_container import DIContainer, PluginRegistry
from power_core.exceptions import (
    ApplicationError,
    ConfigurationError,
    ConnectionError,
    DIError,
    PluginError,
)

__all__ = [
    "Application",
    "DIContainer",
    "PluginRegistry",
    "ApplicationError",
    "ConfigurationError",
    "ConnectionError",
    "DIError",
    "PluginError",
]
