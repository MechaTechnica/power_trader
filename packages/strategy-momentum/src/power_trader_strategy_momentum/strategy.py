"""Momentum trading strategy implementation."""

from datetime import datetime
from typing import Any

from power_framework.protocols.lifecycle import Lifecycle
from power_market.types.market import MarketContext
from power_market.types.signals import Signal, SignalIntent, SignalSource


class MomentumStrategy(Lifecycle):
    """
    Momentum-based trading strategy.

    Implements the Strategy protocol as a plugin and the framework Lifecycle
    protocol (a separate, infrastructure-owned concern) for setup/teardown.

    Strategy logic:
    - Calculates simple price momentum
    - Generates BUY signal when momentum is positive and strong
    - Generates SELL signal when momentum is negative and strong
    - Otherwise HOLD

    Note: This is a simplified example. Real strategies would use
    more sophisticated indicators like RSI, MACD, etc.
    """

    def __init__(self, lookback_periods: int = 10) -> None:
        """
        Initialize strategy.

        Args:
            lookback_periods: Number of bars to look back for momentum calculation
        """
        self._lookback_periods = lookback_periods

    @property
    def strategy_name(self) -> str:
        """Strategy identifier."""
        return "momentum-v1"

    @property
    def version(self) -> str:
        """Strategy version."""
        return "0.1.0"

    async def analyze(self, context: MarketContext) -> Signal:
        """
        Analyze market bars and generate trading signal.

        Args:
            context: Market state snapshot (symbol, bars, reference time)

        Returns:
            Signal with recommendation
        """
        bars = context.bars
        if len(bars) < 2:
            # Not enough data - HOLD
            return self._create_signal(SignalIntent.HOLD, 0.5, {"reason": "insufficient_data"})

        # Calculate simple momentum (% change from N bars ago)
        current_price = float(bars[-1].close)
        lookback_idx = max(0, len(bars) - self._lookback_periods - 1)
        past_price = float(bars[lookback_idx].close)

        momentum = (current_price - past_price) / past_price * 100

        # Signal logic
        if momentum > 2.0:  # Strong upward momentum (>2%)
            intent = SignalIntent.BUY
            confidence = min(0.5 + (momentum / 10), 0.95)
        elif momentum < -2.0:  # Strong downward momentum (<-2%)
            intent = SignalIntent.SELL
            confidence = min(0.5 + (abs(momentum) / 10), 0.95)
        else:  # Weak momentum
            intent = SignalIntent.HOLD
            confidence = 0.6

        # Calculate additional metrics
        volume_avg = sum(bar.volume for bar in bars[-5:]) / min(5, len(bars))
        current_volume = bars[-1].volume
        volume_ratio = current_volume / volume_avg if volume_avg > 0 else 1.0

        return self._create_signal(
            intent,
            confidence,
            {
                "momentum_pct": round(momentum, 2),
                "lookback_periods": self._lookback_periods,
                "current_price": round(current_price, 2),
                "volume_ratio": round(volume_ratio, 2),
            },
        )

    async def start(self) -> None:
        """Prepare the strategy (called once on startup)."""
        # Could load ML models, warm up caches, etc.
        pass

    async def stop(self) -> None:
        """Release strategy resources (called on shutdown)."""
        # Could save state, close connections, etc.
        pass

    def _create_signal(
        self, intent: SignalIntent, confidence: float, metadata: dict[str, Any]
    ) -> Signal:
        """Helper to create a trading signal."""
        return Signal(
            intent=intent,
            confidence=confidence,
            generated_at=datetime.now(),
            source=SignalSource(strategy=self.strategy_name, version=self.version),
            metadata=metadata,
        )
