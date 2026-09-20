"""Tests for signal aggregator."""

from datetime import datetime

import pytest
from power_day_trader.adapters.secondary.signal_aggregator import \
    WeightedAverageAggregator
from power_market.types.signals import Signal, SignalIntent, SignalSource


def _make_signal(intent: SignalIntent, confidence: float, strategy: str) -> Signal:
    """Helper to build a Signal with a known source."""
    return Signal(
        intent=intent,
        confidence=confidence,
        generated_at=datetime.now(),
        source=SignalSource(strategy=strategy),
        metadata={},
    )


class TestWeightedAverageAggregator:
    """Tests for WeightedAverageAggregator."""

    def test_single_signal_returns_same(self) -> None:
        """Test that single signal is returned unchanged."""
        aggregator = WeightedAverageAggregator()

        signal = _make_signal(SignalIntent.BUY, 0.8, "test")

        result = aggregator.aggregate_signals([signal])
        assert result.intent == SignalIntent.BUY
        assert result.confidence == 0.8

    def test_unanimous_buy_signals(self) -> None:
        """Test aggregation when all signals are BUY."""
        aggregator = WeightedAverageAggregator()

        signals = [
            _make_signal(SignalIntent.BUY, 0.7, "strategy1"),
            _make_signal(SignalIntent.BUY, 0.9, "strategy2"),
        ]

        result = aggregator.aggregate_signals(signals)
        assert result.intent == SignalIntent.BUY
        assert result.source.strategy == "aggregated"
        assert "strategy_count" in result.metadata

    def test_mixed_signals_majority(self) -> None:
        """Test aggregation with mixed signal intents."""
        aggregator = WeightedAverageAggregator()

        signals = [
            _make_signal(SignalIntent.BUY, 0.9, "strategy1"),
            _make_signal(SignalIntent.SELL, 0.5, "strategy2"),
            _make_signal(SignalIntent.BUY, 0.8, "strategy3"),
        ]

        result = aggregator.aggregate_signals(signals)
        # BUY should win (0.9 + 0.8 = 1.7 > 0.5)
        assert result.intent == SignalIntent.BUY

    def test_empty_signals_raises(self) -> None:
        """Test that empty signal list raises error."""
        aggregator = WeightedAverageAggregator()

        with pytest.raises(ValueError, match="Cannot aggregate empty"):
            aggregator.aggregate_signals([])
