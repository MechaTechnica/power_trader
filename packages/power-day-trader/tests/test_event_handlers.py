"""Tests for the event-driven order flow."""

from datetime import datetime

from power_day_trader.core.event_handlers import SignalToOrderHandler
from power_framework.events import Event, InMemoryEventBus
from power_market.events import OrderFilled, OrderRequested, OrderSubmitted, SignalGenerated
from power_market.types.market import TickerSymbol
from power_market.types.signals import Signal, SignalIntent, SignalSource


class _Collector:
    def __init__(self) -> None:
        self.received: list[Event] = []

    async def handle(self, event: Event) -> None:
        self.received.append(event)


async def test_signal_to_order_handler_emits_order_lifecycle():
    bus = InMemoryEventBus()
    collector = _Collector()
    bus.subscribe(OrderRequested, collector)
    bus.subscribe(OrderSubmitted, collector)
    bus.subscribe(OrderFilled, collector)

    bus.subscribe(SignalGenerated, SignalToOrderHandler(bus))

    signal = Signal(
        intent=SignalIntent.BUY,
        confidence=0.9,
        generated_at=datetime.now(),
        source=SignalSource(strategy="test"),
        quantity=10,
    )
    await bus.publish(SignalGenerated(symbol=TickerSymbol(symbol="AAPL"), signal=signal))

    assert len(collector.received) == 3
    assert isinstance(collector.received[0], OrderRequested)
    assert isinstance(collector.received[1], OrderSubmitted)
    assert isinstance(collector.received[2], OrderFilled)
    assert collector.received[1].order_id == collector.received[2].order_id  # type: ignore[union-attr]


async def test_signal_to_order_handler_ignores_hold_signals():
    bus = InMemoryEventBus()
    collector = _Collector()
    bus.subscribe(OrderRequested, collector)

    bus.subscribe(SignalGenerated, SignalToOrderHandler(bus))

    signal = Signal(
        intent=SignalIntent.HOLD,
        confidence=0.5,
        generated_at=datetime.now(),
        source=SignalSource(strategy="test"),
    )
    await bus.publish(SignalGenerated(symbol=TickerSymbol(symbol="AAPL"), signal=signal))

    assert collector.received == []
