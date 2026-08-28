"""Momentum trading strategy implementation."""

from datetime import datetime

from power_trader_framework.protocols.strategy import IStrategy
from power_trader_framework.types.common import SignalType
from power_trader_framework.types.market import MarketBar
from power_trader_framework.types.signals import TradingSignal


class MomentumStrategy:
    """
    Momentum-based trading strategy.
    
    Implements IStrategy protocol as a plugin.
    
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

    async def analyze(self, bars: list[MarketBar]) -> TradingSignal:
        """
        Analyze market bars and generate trading signal.
        
        Args:
            bars: Historical market bars (oldest to newest)
            
        Returns:
            TradingSignal with recommendation
        """
        if len(bars) < 2:
            # Not enough data - HOLD
            return self._create_signal(SignalType.HOLD, 0.5, {"reason": "insufficient_data"})
        
        # Calculate simple momentum (% change from N bars ago)
        current_price = float(bars[-1].close)
        lookback_idx = max(0, len(bars) - self._lookback_periods - 1)
        past_price = float(bars[lookback_idx].close)
        
        momentum = (current_price - past_price) / past_price * 100
        
        # Signal logic
        if momentum > 2.0:  # Strong upward momentum (>2%)
            signal_type = SignalType.BUY
            confidence = min(0.5 + (momentum / 10), 0.95)
        elif momentum < -2.0:  # Strong downward momentum (<-2%)
            signal_type = SignalType.SELL
            confidence = min(0.5 + (abs(momentum) / 10), 0.95)
        else:  # Weak momentum
            signal_type = SignalType.HOLD
            confidence = 0.6
        
        # Calculate additional metrics
        volume_avg = sum(bar.volume for bar in bars[-5:]) / min(5, len(bars))
        current_volume = bars[-1].volume
        volume_ratio = current_volume / volume_avg if volume_avg > 0 else 1.0
        
        return self._create_signal(
            signal_type,
            confidence,
            {
                "momentum_pct": round(momentum, 2),
                "lookback_periods": self._lookback_periods,
                "current_price": round(current_price, 2),
                "volume_ratio": round(volume_ratio, 2),
            },
        )

    async def initialize(self) -> None:
        """Initialize strategy (called once on startup)."""
        # Could load ML models, warm up caches, etc.
        pass

    async def cleanup(self) -> None:
        """Cleanup strategy resources (called on shutdown)."""
        # Could save state, close connections, etc.
        pass

    def _create_signal(
        self, signal_type: SignalType, confidence: float, metadata: dict
    ) -> TradingSignal:
        """Helper to create trading signal."""
        return TradingSignal(
            signal_type=signal_type,
            confidence=confidence,
            timestamp=datetime.now(),
            strategy_name=self.strategy_name,
            metadata=metadata,
        )
