"""Signal types for trading strategies."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from power_trader_framework.types.common import SignalType


@dataclass(frozen=True, slots=True)
class TradingSignal:
    """
    Trading signal from a strategy.
    
    Args:
        signal_type: BUY, SELL, or HOLD
        confidence: Confidence score (0.0 to 1.0)
        timestamp: When the signal was generated
        strategy_name: Name/ID of the strategy that generated it
        metadata: Additional strategy-specific information
    """

    signal_type: SignalType
    confidence: float
    timestamp: datetime
    strategy_name: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate signal data."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence ({self.confidence}) must be between 0.0 and 1.0"
            )
        if not self.strategy_name or not self.strategy_name.strip():
            raise ValueError("Strategy name cannot be empty")


@dataclass
class SignalMetadata:
    """
    Additional metadata about signal generation.
    
    This is mutable (unlike TradingSignal) as it's built up during processing.
    """

    bars_analyzed:  int
    computation_time_ms: float
    indicators: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def add_indicator(self, name: str, value: float) -> None:
        """Add an indicator to the metadata."""
        self.indicators[name] = value

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)
