"""Framework event bus capability.

Domain events let decoupled components react to the *facts* of a workflow
without being coupled to the component that produced them. The framework owns
the transport (a :class:`EventBus`) and the shared envelope (:class:`Event` /
:class:`DomainEvent`), while each domain declares its own event types on top.

The guarantee the framework adds is *automatic context propagation*: when an
event is published, the ambient correlation/trace IDs are stamped onto the event
so every downstream handler shares the same identity without passing it around
explicitly.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol

from power_framework.observability import current_correlation_id, current_trace_id

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


@dataclass(frozen=True)
class Event:
    """The shared envelope carried by every event.

    The envelope fields (identity, timing, correlation) are cross-cutting and
    owned by the framework; domain event types add their own payload fields.
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str | None = None
    trace_id: str | None = None


class DomainEvent(Event):
    """Marker base for events that carry domain meaning.

    Subclass this in a domain package (e.g. ``power_market``) to distinguish
    business facts from infrastructure noise.
    """


class EventHandler(Protocol):
    """A subscriber that reacts to events of a declared type."""

    async def handle(self, event: Event) -> None:
        """Handle ``event``.

        Handlers receive the concrete event and are responsible for narrowing it
        (e.g. via ``isinstance``) when they only care about a subtype.
        """
        ...


class EventBus(Protocol):
    """Publish/subscribe transport for domain events."""

    def subscribe(self, event_type: type[Any], handler: EventHandler) -> None:
        """Subscribe ``handler`` to ``event_type`` (and its subclasses)."""
        ...

    async def publish(self, event: Event) -> None:
        """Publish ``event`` to every matching handler."""
        ...


class InMemoryEventBus:
    """A process-local, fan-out event bus.

    Dispatch is fire-and-forget with respect to handlers: a failing handler does
    not prevent other handlers from running. Failures are routed to an optional
    ``on_error`` callback (typically a structured logger); when no callback is
    supplied, a failing handler re-raises.
    """

    def __init__(
        self,
        on_error: Callable[[Event, Exception], Awaitable[None]] | None = None,
    ) -> None:
        self._subscribers: dict[type[Any], list[EventHandler]] = defaultdict(list)
        self._on_error = on_error

    def subscribe(self, event_type: type[Any], handler: EventHandler) -> None:
        """Subscribe ``handler`` to ``event_type`` and all of its subclasses."""
        self._subscribers[event_type].append(handler)

    async def publish(self, event: Event) -> None:
        """Stamp ambient context onto ``event`` and dispatch to all handlers."""
        event = self._attach_context(event)
        for handler in self._matching_handlers(type(event)):
            try:
                await handler.handle(event)
            except Exception as exc:
                if self._on_error is not None:
                    await self._on_error(event, exc)
                else:
                    raise

    def _attach_context(self, event: Event) -> Event:
        """Fill in correlation/trace IDs from the ambient context when absent."""
        correlation_id = event.correlation_id or current_correlation_id()
        trace_id = event.trace_id or current_trace_id()
        if correlation_id == event.correlation_id and trace_id == event.trace_id:
            return event
        return replace(event, correlation_id=correlation_id, trace_id=trace_id)

    def _matching_handlers(self, event_type: type[Any]) -> list[EventHandler]:
        """Return handlers subscribed to ``event_type`` or one of its bases."""
        handlers: list[EventHandler] = []
        for subscribed_type, subs in self._subscribers.items():
            if issubclass(event_type, subscribed_type):
                handlers.extend(subs)
        return handlers


__all__ = [
    "DomainEvent",
    "Event",
    "EventBus",
    "EventHandler",
    "InMemoryEventBus",
]
