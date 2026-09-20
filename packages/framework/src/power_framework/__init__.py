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
from power_framework.plugins import Plugin
from power_framework.protocols.container import Container
from power_framework.protocols.lifecycle import Lifecycle, LifecycleRegistry
from power_framework.settings import CoreSettings, JsonFileSettings

__all__ = [
    "ApplicationBase",
    "ApplicationBuilder",
    "Container",
    "CoreSettings",
    "JsonFileSettings",
    "Lifecycle",
    "LifecycleRegistry",
    "Plugin",
    "Runtime",
]
