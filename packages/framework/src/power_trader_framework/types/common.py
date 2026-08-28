"""Common types and enums used throughout the framework."""

from enum import Enum


class SignalType(str, Enum):
    """Trading signal types."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

    def __str__(self) -> str:
        return self.value
