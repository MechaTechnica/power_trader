"""Domain-agnostic protocol definitions for the Power Framework."""

from power_framework.container import Container, Lifetime
from power_framework.protocols.output import OutputPresenter

__all__ = [
    "Container",
    "Lifetime",
    "OutputPresenter",
]
