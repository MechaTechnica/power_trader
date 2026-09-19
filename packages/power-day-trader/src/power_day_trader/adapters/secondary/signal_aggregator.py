"""Signal aggregator implementation."""

from datetime import datetime

from power_market.protocols.strategy import SignalAggregator
from power_market.types.signals import SignalType, TradingSignal


class WeightedAverageAggregator:
    """
    Aggregates signals using weighted average by confidence.
    
    Implementation of SignalAggregator protocol.
    """

    def aggregate_signals(self, signals: list[TradingSignal]) -> TradingSignal:
        """
        Combine multiple signals using weighted average.
        
        Business rules:
        - Weight each signal by its confidence
        - Final signal type is majority vote
        - Final confidence is weighted average
        """
        if not signals:
            raise ValueError("Cannot aggregate empty signal list")
        
        if len(signals) == 1:
            return signals[0]
        
        # Count votes for each signal type
        buy_confidence = sum(s.confidence for s in signals if s.signal_type == SignalType.BUY)
        sell_confidence = sum(
            s.confidence for s in signals if s.signal_type == SignalType.SELL
        )
        hold_confidence = sum(
            s.confidence for s in signals if s.signal_type == SignalType.HOLD
        )
        
        # Determine final signal type
        max_confidence = max(buy_confidence, sell_confidence, hold_confidence)
        if max_confidence == buy_confidence:
            final_type = SignalType.BUY
        elif max_confidence == sell_confidence:
            final_type = SignalType.SELL
        else:
            final_type = SignalType.HOLD
        
        # Calculate weighted average confidence
        total_weight = sum(s.confidence for s in signals)
        final_confidence = max_confidence / total_weight if total_weight > 0 else 0.0
        
        # Combine metadata
        combined_metadata = {
            "strategy_count": len(signals),
            "strategies": [s.strategy_name for s in signals],
            "individual_signals": [
                {"strategy": s.strategy_name, "type": str(s.signal_type), "confidence": s.confidence}
                for s in signals
            ],
        }
        
        return TradingSignal(
            signal_type=final_type,
            confidence=min(final_confidence, 1.0),  # Cap at 1.0
            timestamp=datetime.now(),
            strategy_name="aggregated",
            metadata=combined_metadata,
        )
