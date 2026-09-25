"""Framework event bus contracts.

Domain events let decoupled components react to the *facts* of a workflow
without being coupled to the component that produced them. The framework owns
the *contracts* — the shared envelope (:class:`Event` / :class:`DomainEvent`),
the delivery contract (:class:`EventBus` / :class:`DurableEventBus`), the
subscription model (:class:`EventHandler` / :class:`HandlerSpec`), and the
declaration helper (:func:`event_handler`). Each domain declares its own event
types on top.

The concrete in-process transports (``InMemoryEventBus``, ``QueuedEventBus``)
live in ``power_core.events``; the framework stays a pure contract layer so it
remains a dependency of everything without dragging transport implementation
details into every consumer.

The guarantee the framework adds is *automatic context propagation*: when an
event is published, the ambient correlation/trace IDs are stamped onto the event
so every downstream handler shares the same identity without passing it around
explicitly.

Delivery semantics
------------------
The framework makes the *delivery contract* explicit rather than implicit. An
in-process ``InMemoryEventBus`` guarantees:

- delivery is **in-process** (no persistence, no cross-process transport);
- **no retry after process crash** (events are lost if the process dies);
- a failing handler **does not fail the publisher** (failures are isolated and
  routed to ``on_error``);
- **ordering** and **cancellation** semantics are defined by the chosen
  :class:`Concurrency` mode.

A durable implementation (e.g. a :class:`DurableEventBus` backed by Kafka or a
message queue) may provide stronger guarantees (persistence, at-least-once
delivery, retry after crash) and should document them explicitly.
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from power_framework.exceptions import InfrastructureError


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


class Concurrency(StrEnum):
    """How a bus dispatches an event to its matching handlers.

    - ``SEQUENTIAL``: handlers run one at a time, in subscription order. A slow
      or failing handler delays (but, with error isolation, does not block) the
      next. Useful when handlers need ordering.
    - ``CONCURRENT``: handlers run together via ``asyncio.gather``. Useful when
      handlers are independent and latency matters.
    - ``QUEUED``: the publisher enqueues the event and returns immediately;
      background consumers drain the queue. Useful for decoupling a producer
      from slow consumers.
    """

    SEQUENTIAL = "sequential"
    CONCURRENT = "concurrent"
    QUEUED = "queued"


@dataclass(frozen=True)
class RetryPolicy:
    """A retry policy applied to a handler when it raises a retryable error.

    Retries are *operation-aware*: by default only transient
    :class:`~power_framework.exceptions.InfrastructureError` failures are
    retried. Commands that are not idempotent should not be retried blindly;
    prefer an idempotency key on the command itself.
    """

    max_attempts: int = 3
    delay_seconds: float = 0.0
    retry_on: tuple[type[BaseException], ...] = (InfrastructureError,)


class EventHandler(Protocol):
    """A subscriber that reacts to events of a declared type."""

    async def handle(self, event: Event) -> None:
        """Handle ``event``.

        Handlers receive the concrete event and are responsible for narrowing it
        (e.g. via ``isinstance``) when they only care about a subtype.
        """
        ...


@dataclass(frozen=True)
class HandlerSpec:
    """A declared handler binding: an event type plus its dispatch policy.

    Produced by the :func:`event_handler` decorator and registered via
    :meth:`EventBus.register`. It carries the handler's concurrency and retry
    policy so the bus can apply them uniformly.
    """

    event_type: type[Any]
    handler: EventHandler
    concurrency: Concurrency = Concurrency.SEQUENTIAL
    retry: RetryPolicy | None = None


class EventBus(Protocol):
    """Publish/subscribe transport for domain events.

    The delivery contract (in-process vs durable, at-most-once vs at-least-once)
    is defined by the concrete implementation. See the module docstring for the
    guarantees the in-memory implementation provides.
    """

    def subscribe(self, event_type: type[Any], handler: EventHandler) -> None:
        """Subscribe ``handler`` to ``event_type`` (and its subclasses)."""
        ...

    def register(self, spec: HandlerSpec) -> None:
        """Register a :class:`HandlerSpec` (event type + handler + policy)."""
        ...

    async def publish(self, event: Event) -> None:
        """Publish ``event`` to every matching handler."""
        ...


class DurableEventBus(EventBus, Protocol):
    """An event bus with persistence and delivery guarantees.

    Unlike the in-process bus, a durable bus survives process restarts and can
    provide at-least-once (or exactly-once) delivery. Implementations (Kafka,
    Azure Event Hubs, RabbitMQ) must document their exact guarantees.
    """

    async def publish(self, event: Event) -> None:
        """Durably publish ``event`` (persisted before returning)."""
        ...


class _FunctionHandler:
    """Adapts a plain ``async def (event)`` function to the ``EventHandler`` shape."""

    def __init__(self, fn: Callable[[Event], Awaitable[None]]) -> None:
        self._fn = fn

    async def handle(self, event: Event) -> None:
        await self._fn(event)


def event_handler(
    event_type: type[Any],
    *,
    concurrency: Concurrency = Concurrency.SEQUENTIAL,
    retry: RetryPolicy | None = None,
) -> Callable[[Callable[[Event], Awaitable[None]]], HandlerSpec]:
    """Declare an event handler with its concurrency and retry policy.

    Usage::

        @event_handler(OrderSubmitted, concurrency=Concurrency.CONCURRENT, retry=RetryPolicy())
        async def on_order_submitted(event: OrderSubmitted) -> None:
            ...

        bus.register(on_order_submitted)

    The decorated function is adapted to the :class:`EventHandler` shape and
    wrapped in a :class:`HandlerSpec`, so it can be registered directly via
    :meth:`EventBus.register`.
    """

    def decorator(fn: Callable[[Event], Awaitable[None]]) -> HandlerSpec:
        return HandlerSpec(
            event_type=event_type,
            handler=_FunctionHandler(fn),
            concurrency=concurrency,
            retry=retry,
        )

    return decorator


__all__ = [
    "Concurrency",
    "DomainEvent",
    "DurableEventBus",
    "Event",
    "EventBus",
    "EventHandler",
    "HandlerSpec",
    "RetryPolicy",
    "event_handler",
]
