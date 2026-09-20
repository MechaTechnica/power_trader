"""Signal aggregator implementation."""

from datetime import datetime

from power_market.types.signals import Signal, SignalIntent, SignalSource


class WeightedAverageAggregator:
    """
    Aggregates signals using weighted average by confidence.

    Implementation of SignalAggregator protocol.
    """

    def aggregate_signals(self, signals: list[Signal]) -> Signal:
        """
        Combine multiple signals using weighted average.

        Business rules:
        - Weight each signal by its confidence
        - Final signal intent is majority vote
        - Final confidence is weighted average
        """
        if not signals:
            raise ValueError("Cannot aggregate empty signal list")

        if len(signals) == 1:
            return signals[0]

        # Count votes for each intent
        buy_confidence = sum(s.confidence for s in signals if s.intent == SignalIntent.BUY)
        sell_confidence = sum(s.confidence for s in signals if s.intent == SignalIntent.SELL)
        hold_confidence = sum(s.confidence for s in signals if s.intent == SignalIntent.HOLD)

        # Determine final intent
        max_confidence = max(buy_confidence, sell_confidence, hold_confidence)
        if max_confidence == buy_confidence:
            final_intent = SignalIntent.BUY
        elif max_confidence == sell_confidence:
            final_intent = SignalIntent.SELL
        else:
            final_intent = SignalIntent.HOLD

        # Calculate weighted average confidence
        total_weight = sum(s.confidence for s in signals)
        final_confidence = max_confidence / total_weight if total_weight > 0 else 0.0

        # Combine metadata
        combined_metadata = {
            "strategy_count": len(signals),
            "strategies": [s.source.strategy for s in signals],
            "individual_signals": [
                {"strategy": s.source.strategy, "type": str(s.intent), "confidence": s.confidence}
                for s in signals
            ],
        }

        return Signal(
            intent=final_intent,
            confidence=min(final_confidence, 1.0),  # Cap at 1.0
            generated_at=datetime.now(),
            source=SignalSource(strategy="aggregated"),
            metadata=combined_metadata,
        )
