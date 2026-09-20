"""Tests for GEX strategy."""

from datetime import datetime
from decimal import Decimal

from power_market.types.market import MarketBar, MarketContext, TickerSymbol
from power_market.types.signals import SignalIntent
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

        signal = await strategy.analyze(create_context([]))
        assert signal.intent == SignalIntent.HOLD
        assert "reason" in signal.metadata

    async def test_analyze_with_mock_data(self) -> None:
        """Test analysis with mock market data."""
        strategy = GEXStrategy(calculator=GEXCalculator())

        bars = [create_test_bar(100.0) for _ in range(10)]

        signal = await strategy.analyze(create_context(bars))

        # Should generate some signal
        assert signal.intent in [SignalIntent.BUY, SignalIntent.SELL, SignalIntent.HOLD]
        assert 0.0 <= signal.confidence <= 1.0
        assert "current_price" in signal.metadata
        assert "total_gex" in signal.metadata

    async def test_metadata_includes_gex_info(self) -> None:
        """Test that signal metadata includes GEX information."""
        strategy = GEXStrategy(calculator=GEXCalculator())

        bars = [create_test_bar(100.0)]
        signal = await strategy.analyze(create_context(bars))

        # Check for expected metadata fields
        assert "total_gex" in signal.metadata
        assert "gex_environment" in signal.metadata
        assert signal.metadata["gex_environment"] in ["positive", "negative"]

    async def test_start_and_stop(self) -> None:
        """Test lifecycle methods."""
        strategy = GEXStrategy(calculator=GEXCalculator())

        # Should not raise
        await strategy.start()
        await strategy.stop()

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
        signal = await strategy.analyze(create_context(bars))

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


def create_context(bars: list[MarketBar]) -> MarketContext:
    """Helper to wrap bars in a MarketContext."""
    symbol = bars[0].symbol if bars else TickerSymbol(symbol="SPY")
    timestamp = bars[-1].timestamp if bars else datetime.now()
    return MarketContext(symbol=symbol, bars=bars, timestamp=timestamp)
