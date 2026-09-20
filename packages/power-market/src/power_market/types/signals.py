"""Signal types for trading strategies."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any


class SignalIntent(str, Enum):
    """The action a strategy intends the trader to take."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class SignalSource:
    """
    Identifies the strategy (and version) that produced a signal.

    Args:
        strategy: Unique strategy identifier (e.g., "momentum-v1")
        version: Strategy version (e.g., "0.1.0")
    """

    strategy: str
    version: str = ""

    def __post_init__(self) -> None:
        """Validate source."""
        if not self.strategy or not self.strategy.strip():
            raise ValueError("Strategy cannot be empty")


@dataclass(frozen=True, slots=True)
class Signal:
    """
    Trading signal produced by a strategy.

    A signal captures the strategy's *intent* plus enough context to act on
    it: how confident it is, when it was generated, when it expires, and which
    strategy produced it. Optional ``quantity``/``price`` fields allow sizing
    and target information without forcing every strategy to supply them, and
    ``reason`` carries the human-readable rationale behind the intent.

    Args:
        intent: BUY, SELL, or HOLD
        confidence: Confidence score (0.0 to 1.0)
        generated_at: When the signal was generated
        source: Strategy (and version) that produced the signal
        valid_until: Optional expiry after which the signal should be ignored
        reason: Optional human-readable rationale for the intent
        quantity: Optional position sizing suggestion
        price: Optional target/limit price suggestion
        metadata: Additional strategy-specific information
    """

    intent: SignalIntent
    confidence: float
    generated_at: datetime
    source: SignalSource
    valid_until: datetime | None = None
    reason: str | None = None
    quantity: Decimal | None = None
    price: Decimal | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate signal data."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence ({self.confidence}) must be between 0.0 and 1.0"
            )


@dataclass
class SignalMetadata:
    """
    Additional metadata about signal generation.

    This is mutable (unlike Signal) as it's built up during processing.
    """

    bars_analyzed: int
    computation_time_ms: float
    indicators: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def add_indicator(self, name: str, value: float) -> None:
        """Add an indicator to the metadata."""
        self.indicators[name] = value

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)
