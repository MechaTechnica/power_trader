"""Domain-agnostic protocol definitions for the Power Framework."""

from power_framework.protocols.container import Container, Lifetime
from power_framework.protocols.lifecycle import Lifecycle, LifecycleRegistry
from power_framework.protocols.output import OutputPresenter

__all__ = [
    "Container",
    "Lifecycle",
    "LifecycleRegistry",
    "Lifetime",
    "OutputPresenter",
]
