"""Trading-domain events.

These are the domain vocabulary emitted along the trading pipeline::

    MarketDataReceived
        ↓  (strategy)
    SignalGenerated
        ↓  (risk / execution)
    OrderRequested
        ↓
    OrderSubmitted
        ↓
    OrderFilled | OrderRejected

Each is an immutable :class:`DomainEvent` carrying just enough payload for
downstream handlers (risk, execution, audit) to act without coupling to the
producer.
"""

from dataclasses import dataclass
from decimal import Decimal

from power_framework.events import DomainEvent
from power_market.types.market import MarketBar, TickerSymbol
from power_market.types.signals import Signal, SignalIntent


@dataclass(frozen=True, kw_only=True)
class MarketDataReceived(DomainEvent):
    """A market bar was received for a symbol."""

    symbol: TickerSymbol
    bar: MarketBar


@dataclass(frozen=True, kw_only=True)
class SignalGenerated(DomainEvent):
    """A strategy produced a signal for a symbol."""

    symbol: TickerSymbol
    signal: Signal


@dataclass(frozen=True, kw_only=True)
class OrderRequested(DomainEvent):
    """Risk approved an order request (intent to trade)."""

    symbol: TickerSymbol
    intent: SignalIntent
    quantity: Decimal
    signal: Signal | None = None


@dataclass(frozen=True, kw_only=True)
class OrderSubmitted(DomainEvent):
    """An order was submitted to the execution venue."""

    order_id: str
    symbol: TickerSymbol
    intent: SignalIntent
    quantity: Decimal


@dataclass(frozen=True, kw_only=True)
class OrderFilled(DomainEvent):
    """An order was filled."""

    order_id: str
    symbol: TickerSymbol
    quantity: Decimal
    fill_price: Decimal


@dataclass(frozen=True, kw_only=True)
class OrderRejected(DomainEvent):
    """An order was rejected."""

    order_id: str
    symbol: TickerSymbol
    reason: str


__all__ = [
    "MarketDataReceived",
    "OrderFilled",
    "OrderRejected",
    "OrderRequested",
    "OrderSubmitted",
    "SignalGenerated",
]
