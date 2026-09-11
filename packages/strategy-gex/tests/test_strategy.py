"""Tests for GEX strategy."""

from datetime import datetime
from decimal import Decimal

import pytest
from power_trader_framework.types.common import SignalType
from power_trader_framework.types.market import MarketBar, TickerSymbol
from power_trader_strategy_gex.gex_calculator import GEXCalculator
from power_trader_strategy_gex.strategy import GEXStrategy


class TestGEXStrategy:
    """Tests for GEXStrategy."""

    def test_strategy_properties(self) -> None:
        """Test strategy name and version."""
        strategy = GEXStrategy(calculator=GEXCalculator())
        assert strategy.strategy_name == "gex-v1"
        assert strategy.version == "0.1.0"

    async def test_no_bars_returns_hold(self) -> None:
        """Test that no data returns HOLD signal."""
        strategy = GEXStrategy(calculator=GEXCalculator())

        signal = await strategy.analyze([])
        assert signal.signal_type == SignalType.HOLD
        assert "reason" in signal.metadata

    async def test_analyze_with_mock_data(self) -> None:
        """Test analysis with mock market data."""
        strategy = GEXStrategy(calculator=GEXCalculator())

        bars = [create_test_bar(100.0) for _ in range(10)]

        signal = await strategy.analyze(bars)

        # Should generate some signal
        assert signal.signal_type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
        assert 0.0 <= signal.confidence <= 1.0
        assert "current_price" in signal.metadata
        assert "total_gex" in signal.metadata

    async def test_metadata_includes_gex_info(self) -> None:
        """Test that signal metadata includes GEX information."""
        strategy = GEXStrategy(calculator=GEXCalculator())

        bars = [create_test_bar(100.0)]
        signal = await strategy.analyze(bars)

        # Check for expected metadata fields
        assert "total_gex" in signal.metadata
        assert "gex_environment" in signal.metadata
        assert signal.metadata["gex_environment"] in ["positive", "negative"]

    async def test_initialize_and_cleanup(self) -> None:
        """Test lifecycle methods."""
        strategy = GEXStrategy(calculator=GEXCalculator())

        # Should not raise
        await strategy.initialize()
        await strategy.cleanup()

    async def test_custom_parameters(self) -> None:
        """Test strategy with custom parameters."""
        strategy = GEXStrategy(
            calculator=GEXCalculator(),
            lookback_days=60,
            proximity_threshold=0.05,
            min_gex_strength=0.5,
        )

        assert strategy.lookback_days == 60
        assert strategy.proximity_threshold == 0.05
        assert strategy.min_gex_strength == 0.5

        bars = [create_test_bar(100.0)]
        signal = await strategy.analyze(bars)

        # Should still work
        assert signal is not None


def create_test_bar(price: float) -> MarketBar:
    """Helper to create test market bar."""
    return MarketBar(
        symbol=TickerSymbol(symbol="SPY"),
        timestamp=datetime.now(),
        open=Decimal(str(price)),
        high=Decimal(str(price * 1.01)),
        low=Decimal(str(price * 0.99)),
        close=Decimal(str(price)),
        volume=1000000,
    )
