"""Event-driven order flow.

React to domain events by translating actionable signals into the order
lifecycle events (``OrderRequested`` → ``OrderSubmitted`` → ``OrderFilled`` /
``OrderRejected``). This demonstrates the decoupled, event-driven chain that the
same framework translates directly to a bank application::

    input event → domain service → domain event → risk/validation → infrastructure
"""

import itertools
from decimal import Decimal

from power_framework.events import Event, EventBus
from power_market.events import (OrderFilled, OrderRequested, OrderSubmitted,
                                 SignalGenerated)
from power_market.types.signals import SignalIntent


class SignalToOrderHandler:
    """Translate actionable signals into the order lifecycle events.

    This is a paper/naive executor for the POC: it subscribes to
    :class:`SignalGenerated` and, for non-HOLD intents, emits the order flow. A
    real execution adapter would subscribe here and route to a broker instead.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._counter = itertools.count(1)

    async def handle(self, event: Event) -> None:
        if not isinstance(event, SignalGenerated):
            return
        signal = event.signal
        if signal.intent is SignalIntent.HOLD:
            return

        quantity = signal.quantity or Decimal("1")
        order_id = f"ord-{next(self._counter)}"

        await self._event_bus.publish(
            OrderRequested(
                symbol=event.symbol,
                intent=signal.intent,
                quantity=quantity,
                signal=signal,
            )
        )
        await self._event_bus.publish(
            OrderSubmitted(
                order_id=order_id,
                symbol=event.symbol,
                intent=signal.intent,
                quantity=quantity,
            )
        )
        await self._event_bus.publish(
            OrderFilled(
                order_id=order_id,
                symbol=event.symbol,
                quantity=quantity,
                fill_price=signal.price or Decimal("0"),
            )
        )
