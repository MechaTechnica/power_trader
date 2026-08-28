"""Tests for momentum strategy."""

from datetime import datetime
from decimal import Decimal

import pytest
from power_trader_framework.types.common import SignalType
from power_trader_framework.types.market import MarketBar, TickerSymbol
from power_trader_strategy_momentum.strategy import MomentumStrategy


class TestMomentumStrategy:
    """Tests for MomentumStrategy."""

    def test_strategy_properties(self) -> None:
        """Test strategy name and version."""
        strategy = MomentumStrategy()
        assert strategy.strategy_name == "momentum-v1"
        assert strategy.version == "0.1.0"

    async def test_insufficient_data_returns_hold(self) -> None:
        """Test that insufficient data returns HOLD signal."""
        strategy = MomentumStrategy()
        
        # Single bar
        bars = [create_test_bar(100.0)]
        
        signal = await strategy.analyze(bars)
        assert signal.signal_type == SignalType.HOLD
        assert "reason" in signal.metadata

    async def test_strong_upward_momentum_returns_buy(self) -> None:
        """Test that strong upward momentum returns BUY."""
        strategy = MomentumStrategy(lookback_periods=5)
        
        # Create bars with strong upward trend
        bars = [
            create_test_bar(100.0),
            create_test_bar(101.0),
            create_test_bar(102.0),
            create_test_bar(103.0),
            create_test_bar(104.0),
            create_test_bar(105.0),  # 5% gain
        ]
        
        signal = await strategy.analyze(bars)
        assert signal.signal_type == SignalType.BUY
        assert signal.confidence > 0.5
        assert "momentum_pct" in signal.metadata

    async def test_strong_downward_momentum_returns_sell(self) -> None:
        """Test that strong downward momentum returns SELL."""
        strategy = MomentumStrategy(lookback_periods=5)
        
        # Create bars with strong downward trend
        bars = [
            create_test_bar(100.0),
            create_test_bar(99.0),
            create_test_bar(98.0),
            create_test_bar(97.0),
            create_test_bar(96.0),
            create_test_bar(95.0),  # 5% loss
        ]
        
        signal = await strategy.analyze(bars)
        assert signal.signal_type == SignalType.SELL
        assert signal.confidence > 0.5

    async def test_weak_momentum_returns_hold(self) -> None:
        """Test that weak momentum returns HOLD."""
        strategy = MomentumStrategy()
        
        # Create bars with minimal change
        bars = [
            create_test_bar(100.0),
            create_test_bar(100.5),
            create_test_bar(99.5),
            create_test_bar(100.2),
        ]
        
        signal = await strategy.analyze(bars)
        assert signal.signal_type == SignalType.HOLD

    async def test_initialize_and_cleanup(self) -> None:
        """Test lifecycle methods."""
        strategy = MomentumStrategy()
        
        # Should not raise
        await strategy.initialize()
        await strategy.cleanup()


def create_test_bar(price: float) -> MarketBar:
    """Helper to create test market bar."""
    return MarketBar(
        symbol=TickerSymbol(symbol="TEST"),
        timestamp=datetime.now(),
        open=Decimal(str(price)),
        high=Decimal(str(price * 1.01)),
        low=Decimal(str(price * 0.99)),
        close=Decimal(str(price)),
        volume=1000000,
    )
