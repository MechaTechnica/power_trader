"""Tests for framework types."""

from datetime import datetime
from decimal import Decimal

import pytest
from power_market.types.market import (MarketBar, MarketContext, TickerSymbol,
                                       TimeInterval)
from power_market.types.signals import (Signal, SignalIntent, SignalMetadata,
                                        SignalSource)


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


class TestMarketContext:
    """Tests for MarketContext type."""

    def test_create_context(self) -> None:
        """Test creating a market context."""
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
        context = MarketContext(symbol=symbol, bars=[bar], timestamp=bar.timestamp)
        assert context.symbol == symbol
        assert list(context.bars) == [bar]
        assert context.timestamp == bar.timestamp

    def test_context_is_immutable(self) -> None:
        """Test that MarketContext is immutable."""
        symbol = TickerSymbol(symbol="AAPL")
        context = MarketContext(symbol=symbol, bars=[], timestamp=datetime.now())
        with pytest.raises(AttributeError):
            context.symbol = TickerSymbol(symbol="MSFT")  # type: ignore


class TestSignalSource:
    """Tests for SignalSource type."""

    def test_create_source(self) -> None:
        """Test creating a valid signal source."""
        source = SignalSource(strategy="momentum-v1", version="0.1.0")
        assert source.strategy == "momentum-v1"
        assert source.version == "0.1.0"

    def test_empty_strategy_raises(self) -> None:
        """Test that empty strategy raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            SignalSource(strategy="")


class TestSignal:
    """Tests for Signal type."""

    def test_create_valid_signal(self) -> None:
        """Test creating a valid trading signal."""
        signal = Signal(
            intent=SignalIntent.BUY,
            confidence=0.85,
            generated_at=datetime.now(),
            source=SignalSource(strategy="test-strategy"),
            metadata={"rsi": 65.0},
        )
        assert signal.intent == SignalIntent.BUY
        assert signal.confidence == 0.85
        assert signal.metadata["rsi"] == 65.0
        assert signal.source.strategy == "test-strategy"

    def test_confidence_out_of_range_raises(self) -> None:
        """Test that confidence out of range raises ValueError."""
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            Signal(
                intent=SignalIntent.BUY,
                confidence=1.5,  # Too high!
                generated_at=datetime.now(),
                source=SignalSource(strategy="test-strategy"),
            )

    def test_optional_fields_default_to_none(self) -> None:
        """Test that optional signal fields default to None."""
        signal = Signal(
            intent=SignalIntent.HOLD,
            confidence=0.5,
            generated_at=datetime.now(),
            source=SignalSource(strategy="test-strategy"),
        )
        assert signal.valid_until is None
        assert signal.reason is None
        assert signal.quantity is None
        assert signal.price is None


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
