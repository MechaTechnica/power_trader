"""Market data types - using dataclasses for performance in hot paths."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class TickerSymbol:
    """
    Immutable ticker symbol representation.
    
    Args:
        symbol: The ticker symbol (e.g., 'AAPL')
        exchange: Optional exchange identifier (e.g., 'NASDAQ')
    """

    symbol: str
    exchange: str | None = None

    def __str__(self) -> str:
        """Return string representation of ticker."""
        return f"{self.symbol}:{self.exchange}" if self.exchange else self.symbol

    def __post_init__(self) -> None:
        """Validate ticker symbol."""
        if not self.symbol or not self.symbol.strip():
            raise ValueError("Symbol cannot be empty")


@dataclass(frozen=True, slots=True)
class MarketBar:
    """
    OHLCV bar data - using dataclass with slots for performance.
    
    This is used in the hot path (streaming market data), so we optimize:
    - frozen=True for immutability and hashability
    - slots=True for memory efficiency
    - Decimal for price precision
    """

    symbol: TickerSymbol
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int

    def __post_init__(self) -> None:
        """Validate bar data."""
        # Validation in hot path should be minimal but critical
        if self.high < self.low:
            raise ValueError(f"High ({self.high}) must be >= low ({self.low})")
        if self.volume < 0:
            raise ValueError(f"Volume ({self.volume}) cannot be negative")


@dataclass(frozen=True, slots=True)
class TimeInterval:
    """Time interval representation for bar data."""

    seconds: int

    @classmethod
    def from_minutes(cls, minutes: int) -> "TimeInterval":
        """Create interval from minutes."""
        return cls(seconds=minutes * 60)

    @classmethod
    def from_seconds(cls, seconds: int) -> "TimeInterval":
        """Create interval from seconds."""
        return cls(seconds=seconds)

    def __post_init__(self) -> None:
        """Validate interval."""
        if self.seconds <= 0:
            raise ValueError(f"Interval ({self.seconds}s) must be positive")

    def __str__(self) -> str:
        """Return human-readable interval."""
        if self.seconds >= 60:
            minutes = self.seconds // 60
            return f"{minutes}m" if self.seconds % 60 == 0 else f"{self.seconds}s"
        return f"{self.seconds}s"


@dataclass(frozen=True, slots=True)
class MarketContext:
    """
    Snapshot of market state handed to a strategy for analysis.

    This is the *stable* input surface for strategies. Instead of passing a
    bare ``list[MarketBar]`` (which locks strategies into a single data shape),
    strategies receive a context object that can grow to carry quotes, options,
    fundamentals, news, market state, position, and account state without
    changing the strategy interface.

    Args:
        symbol: The symbol being analyzed
        bars: Historical market bars (ordered oldest to newest)
        timestamp: The reference time of this context snapshot
    """

    symbol: TickerSymbol
    bars: Sequence[MarketBar]
    timestamp: datetime
