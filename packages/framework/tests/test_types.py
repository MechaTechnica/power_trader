"""Tests for framework types."""

from datetime import datetime
from decimal import Decimal

import pytest
from power_trader_framework.types.market import (MarketBar, TickerSymbol,
                                                 TimeInterval)
from power_trader_framework.types.signals import (SignalMetadata, SignalType,
                                                  TradingSignal)


class TestTickerSymbol:
    """Tests for TickerSymbol type."""

    def test_create_simple_symbol(self) -> None:
        """Test creating a simple ticker symbol."""
        symbol = TickerSymbol(symbol="AAPL")
        assert symbol.symbol == "AAPL"
        assert symbol.exchange is None
        assert str(symbol) == "AAPL"

    def test_create_symbol_with_exchange(self) -> None:
        """Test creating a ticker with exchange."""
        symbol = TickerSymbol(symbol="AAPL", exchange="NASDAQ")
        assert symbol.symbol == "AAPL"
        assert symbol.exchange == "NASDAQ"
        assert str(symbol) == "AAPL:NASDAQ"

    def test_empty_symbol_raises(self) -> None:
        """Test that empty symbol raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            TickerSymbol(symbol="")

    def test_symbol_is_immutable(self) -> None:
        """Test that TickerSymbol is immutable."""
        symbol = TickerSymbol(symbol="AAPL")
        with pytest.raises(AttributeError):
            symbol.symbol = "MSFT"  # type: ignore


class TestMarketBar:
    """Tests for MarketBar type."""

    def test_create_valid_bar(self) -> None:
        """Test creating a valid market bar."""
        symbol = TickerSymbol(symbol="AAPL")
        bar = MarketBar(
            symbol=symbol,
            timestamp=datetime.now(),
            open=Decimal("100.00"),
            high=Decimal("101.00"),
            low=Decimal("99.00"),
            close=Decimal("100.50"),
            volume=1000000,
        )
        assert bar.symbol == symbol
        assert bar.high == Decimal("101.00")
        assert bar.volume == 1000000

    def test_high_less_than_low_raises(self) -> None:
        """Test that high < low raises ValueError."""
        symbol = TickerSymbol(symbol="AAPL")
        with pytest.raises(ValueError, match="High .* must be >= low"):
            MarketBar(
                symbol=symbol,
                timestamp=datetime.now(),
                open=Decimal("100.00"),
                high=Decimal("99.00"),  # Lower than low!
                low=Decimal("100.00"),
                close=Decimal("100.00"),
                volume=1000,
            )

    def test_negative_volume_raises(self) -> None:
        """Test that negative volume raises ValueError."""
        symbol = TickerSymbol(symbol="AAPL")
        with pytest.raises(ValueError, match="cannot be negative"):
            MarketBar(
                symbol=symbol,
                timestamp=datetime.now(),
                open=Decimal("100.00"),
                high=Decimal("101.00"),
                low=Decimal("99.00"),
                close=Decimal("100.00"),
                volume=-1000,
            )

    def test_bar_is_immutable(self) -> None:
        """Test that MarketBar is immutable."""
        symbol = TickerSymbol(symbol="AAPL")
        bar = MarketBar(
            symbol=symbol,
            timestamp=datetime.now(),
            open=Decimal("100.00"),
            high=Decimal("101.00"),
            low=Decimal("99.00"),
            close=Decimal("100.50"),
            volume=1000000,
        )
        with pytest.raises(AttributeError):
            bar.volume = 2000000  # type: ignore


class TestTimeInterval:
    """Tests for TimeInterval type."""

    def test_from_seconds(self) -> None:
        """Test creating interval from seconds."""
        interval = TimeInterval.from_seconds(30)
        assert interval.seconds == 30
        assert str(interval) == "30s"

    def test_from_minutes(self) -> None:
        """Test creating interval from minutes."""
        interval = TimeInterval.from_minutes(5)
        assert interval.seconds == 300
        assert str(interval) == "5m"

    def test_zero_interval_raises(self) -> None:
        """Test that zero interval raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            TimeInterval(seconds=0)

    def test_negative_interval_raises(self) -> None:
        """Test that negative interval raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            TimeInterval(seconds=-60)


class TestTradingSignal:
    """Tests for TradingSignal type."""

    def test_create_valid_signal(self) -> None:
        """Test creating a valid trading signal."""
        signal = TradingSignal(
            signal_type=SignalType.BUY,
            confidence=0.85,
            timestamp=datetime.now(),
            strategy_name="test-strategy",
            metadata={"rsi": 65.0},
        )
        assert signal.signal_type == SignalType.BUY
        assert signal.confidence == 0.85
        assert signal.metadata["rsi"] == 65.0

    def test_confidence_out_of_range_raises(self) -> None:
        """Test that confidence out of range raises ValueError."""
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            TradingSignal(
                signal_type=SignalType.BUY,
                confidence=1.5,  # Too high!
                timestamp=datetime.now(),
                strategy_name="test-strategy",
            )

    def test_empty_strategy_name_raises(self) -> None:
        """Test that empty strategy name raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            TradingSignal(
                signal_type=SignalType.BUY,
                confidence=0.85,
                timestamp=datetime.now(),
                strategy_name="",  # Empty!
            )


class TestSignalMetadata:
    """Tests for SignalMetadata type."""

    def test_create_metadata(self) -> None:
        """Test creating signal metadata."""
        metadata = SignalMetadata(
            bars_analyzed=100,
            computation_time_ms=15.5,
        )
        assert metadata.bars_analyzed == 100
        assert metadata.computation_time_ms == 15.5
        assert len(metadata.indicators) == 0
        assert len(metadata.warnings) == 0

    def test_add_indicator(self) -> None:
        """Test adding indicators to metadata."""
        metadata = SignalMetadata(bars_analyzed=100, computation_time_ms=15.5)
        metadata.add_indicator("rsi", 65.0)
        metadata.add_indicator("macd", 0.5)
        
        assert metadata.indicators["rsi"] == 65.0
        assert metadata.indicators["macd"] == 0.5

    def test_add_warning(self) -> None:
        """Test adding warnings to metadata."""
        metadata = SignalMetadata(bars_analyzed=100, computation_time_ms=15.5)
        metadata.add_warning("Low volume detected")
        metadata.add_warning("High volatility")
        
        assert len(metadata.warnings) == 2
        assert "Low volume" in metadata.warnings[0]
