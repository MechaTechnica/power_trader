"""Tests for trading-domain events."""

from datetime import datetime
from decimal import Decimal

from power_framework.events import DomainEvent
from power_market.events import (MarketDataReceived, OrderFilled,
                                 OrderRejected, OrderRequested, OrderSubmitted,
                                 SignalGenerated)
from power_market.types.market import MarketBar, TickerSymbol
from power_market.types.signals import Signal, SignalIntent, SignalSource


def _make_bar(price: float = 100.0) -> MarketBar:
    return MarketBar(
        symbol=TickerSymbol(symbol="AAPL"),
        timestamp=datetime.now(),
        open=Decimal(str(price)),
        high=Decimal(str(price * 1.01)),
        low=Decimal(str(price * 0.99)),
        close=Decimal(str(price)),
        volume=1_000_000,
    )


def _make_signal(intent: SignalIntent = SignalIntent.BUY) -> Signal:
    return Signal(
        intent=intent,
        confidence=0.8,
        generated_at=datetime.now(),
        source=SignalSource(strategy="test"),
    )


def test_domain_events_are_domain_events():
    symbol = TickerSymbol(symbol="AAPL")
    assert isinstance(MarketDataReceived(symbol=symbol, bar=_make_bar()), DomainEvent)
    assert isinstance(
        SignalGenerated(symbol=symbol, signal=_make_signal()), DomainEvent
    )


def test_market_data_received_carries_payload_and_identity():
    symbol = TickerSymbol(symbol="AAPL")
    bar = _make_bar()
    event = MarketDataReceived(symbol=symbol, bar=bar)

    assert event.symbol is symbol
    assert event.bar is bar
    assert event.event_id
    assert event.timestamp is not None


def test_signal_generated_carries_signal():
    symbol = TickerSymbol(symbol="AAPL")
    signal = _make_signal()
    event = SignalGenerated(symbol=symbol, signal=signal)

    assert event.signal is signal
    assert event.symbol is symbol


def test_order_lifecycle_events_carry_payload():
    symbol = TickerSymbol(symbol="AAPL")

    requested = OrderRequested(
        symbol=symbol, intent=SignalIntent.BUY, quantity=Decimal("10")
    )
    submitted = OrderSubmitted(
        order_id="ord-1", symbol=symbol, intent=SignalIntent.BUY, quantity=Decimal("10")
    )
    filled = OrderFilled(
        order_id="ord-1", symbol=symbol, quantity=Decimal("10"), fill_price=Decimal("100.5")
    )
    rejected = OrderRejected(order_id="ord-2", symbol=symbol, reason="risk limit")

    assert requested.quantity == Decimal("10")
    assert submitted.order_id == "ord-1"
    assert filled.fill_price == Decimal("100.5")
    assert rejected.reason == "risk limit"
