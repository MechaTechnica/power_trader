"""Common enums and types shared across the framework.

This module exists for backward-compatible imports; ``SignalType`` is
canonically defined in :mod:`power_trader_framework.types.signals`.
"""

from power_trader_framework.types.signals import SignalType

__all__ = ["SignalType"]
