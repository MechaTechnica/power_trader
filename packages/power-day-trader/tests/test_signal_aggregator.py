"""Tests for signal aggregator."""

from datetime import datetime

import pytest
from power_day_trader.adapters.secondary.signal_aggregator import WeightedAverageAggregator
from power_framework.types.common import SignalType
from power_framework.types.signals import TradingSignal


class TestWeightedAverageAggregator:
    """Tests for WeightedAverageAggregator."""

    def test_single_signal_returns_same(self) -> None:
        """Test that single signal is returned unchanged."""
        aggregator = WeightedAverageAggregator()
        
        signal = TradingSignal(
            signal_type=SignalType.BUY,
            confidence=0.8,
            timestamp=datetime.now(),
            strategy_name="test",
            metadata={},
        )
        
        result = aggregator.aggregate_signals([signal])
        assert result.signal_type == SignalType.BUY
        assert result.confidence == 0.8

    def test_unanimous_buy_signals(self) -> None:
        """Test aggregation when all signals are BUY."""
        aggregator = WeightedAverageAggregator()
        
        signals = [
            TradingSignal(
                signal_type=SignalType.BUY,
                confidence=0.7,
                timestamp=datetime.now(),
                strategy_name="strategy1",
                metadata={},
            ),
            TradingSignal(
                signal_type=SignalType.BUY,
                confidence=0.9,
                timestamp=datetime.now(),
                strategy_name="strategy2",
                metadata={},
            ),
        ]
        
        result = aggregator.aggregate_signals(signals)
        assert result.signal_type == SignalType.BUY
        assert result.strategy_name == "aggregated"
        assert "strategy_count" in result.metadata

    def test_mixed_signals_majority(self) -> None:
        """Test aggregation with mixed signal types."""
        aggregator = WeightedAverageAggregator()
        
        signals = [
            TradingSignal(
                signal_type=SignalType.BUY,
                confidence=0.9,
                timestamp=datetime.now(),
                strategy_name="strategy1",
                metadata={},
            ),
            TradingSignal(
                signal_type=SignalType.SELL,
                confidence=0.5,
                timestamp=datetime.now(),
                strategy_name="strategy2",
                metadata={},
            ),
            TradingSignal(
                signal_type=SignalType.BUY,
                confidence=0.8,
                timestamp=datetime.now(),
                strategy_name="strategy3",
                metadata={},
            ),
        ]
        
        result = aggregator.aggregate_signals(signals)
        # BUY should win (0.9 + 0.8 = 1.7 > 0.5)
        assert result.signal_type == SignalType.BUY

    def test_empty_signals_raises(self) -> None:
        """Test that empty signal list raises error."""
        aggregator = WeightedAverageAggregator()
        
        with pytest.raises(ValueError, match="Cannot aggregate empty"):
            aggregator.aggregate_signals([])
