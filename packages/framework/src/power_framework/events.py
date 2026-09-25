"""Framework event bus capability.

Domain events let decoupled components react to the *facts* of a workflow
without being coupled to the component that produced them. The framework owns
the transport (an :class:`EventBus`) and the shared envelope (:class:`Event` /
:class:`DomainEvent`), while each domain declares its own event types on top.

The guarantee the framework adds is *automatic context propagation*: when an
event is published, the ambient correlation/trace IDs are stamped onto the event
so every downstream handler shares the same identity without passing it around
explicitly.

Delivery semantics
------------------
The framework makes the *delivery contract* explicit rather than implicit. An
in-process :class:`InMemoryEventBus` guarantees:

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

import asyncio
import contextlib
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from power_framework.exceptions import InfrastructureError
from power_framework.observability import (current_correlation_id,
                                           current_trace_id)


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


class InMemoryEventBus:
    """A process-local, fan-out event bus.

    Delivery is **in-process** and **non-durable**: events are not persisted and
    are lost if the process crashes. A failing handler is isolated (it does not
    prevent other handlers from running) and routed to an optional ``on_error``
    callback; when no callback is supplied, a failing handler re-raises.

    Args:
        on_error: Optional async callback ``(event, error)`` for handler failures.
        concurrency: The dispatch mode (``SEQUENTIAL`` by default). ``CONCURRENT``
            runs handlers together; ``QUEUED`` is provided by :class:`QueuedEventBus`.
    """

    def __init__(
        self,
        on_error: Callable[[Event, Exception], Awaitable[None]] | None = None,
        *,
        concurrency: Concurrency = Concurrency.SEQUENTIAL,
    ) -> None:
        self._subscribers: dict[type[Any], list[EventHandler]] = defaultdict(list)
        self._specs: dict[type[Any], list[HandlerSpec]] = defaultdict(list)
        self._on_error = on_error
        self._concurrency = concurrency

    def subscribe(self, event_type: type[Any], handler: EventHandler) -> None:
        """Subscribe ``handler`` to ``event_type`` and all of its subclasses."""
        self._subscribers[event_type].append(handler)

    def register(self, spec: HandlerSpec) -> None:
        """Register a :class:`HandlerSpec` (event type + handler + policy)."""
        self._specs[spec.event_type].append(spec)

    async def publish(self, event: Event) -> None:
        """Stamp ambient context onto ``event`` and dispatch to all handlers."""
        event = self._attach_context(event)
        handlers = self._matching_handlers(type(event))
        specs = self._matching_specs(type(event))

        if self._concurrency is Concurrency.CONCURRENT:
            await asyncio.gather(
                *(self._dispatch(handler, event) for handler in handlers),
                *(self._dispatch_spec(spec, event) for spec in specs),
            )
            return

        # SEQUENTIAL: preserve subscription order and isolate failures.
        for handler in handlers:
            await self._dispatch(handler, event)
        for spec in specs:
            await self._dispatch_spec(spec, event)

    async def _dispatch(self, handler: EventHandler, event: Event) -> None:
        try:
            await handler.handle(event)
        except Exception as exc:
            await self._route_error(event, exc)

    async def _dispatch_spec(self, spec: HandlerSpec, event: Event) -> None:
        if spec.retry is None:
            await self._dispatch(spec.handler, event)
            return

        attempts = 0
        while True:
            attempts += 1
            try:
                await spec.handler.handle(event)
                return
            except spec.retry.retry_on:
                if attempts >= spec.retry.max_attempts:
                    await self._route_error(
                        event,
                        RuntimeError(
                            f"Handler "
                            f"{getattr(spec.handler, '__name__', type(spec.handler).__name__)} "
                            f"failed after {attempts} attempts"
                        ),
                    )
                    return
                if spec.retry.delay_seconds > 0:
                    await asyncio.sleep(spec.retry.delay_seconds)
            # Catch all exceptions, ignore pylint error, catch all is correct
            except Exception as exc:  # pylint: disable=broad-except
                await self._route_error(event, exc)
                return

    async def _route_error(self, event: Event, error: Exception) -> None:
        if self._on_error is not None:
            await self._on_error(event, error)
        else:
            raise error

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

    def _matching_specs(self, event_type: type[Any]) -> list[HandlerSpec]:
        """Return handler specs subscribed to ``event_type`` or one of its bases."""
        specs: list[HandlerSpec] = []
        for subscribed_type, subs in self._specs.items():
            if issubclass(event_type, subscribed_type):
                specs.extend(subs)
        return specs


class QueuedEventBus(InMemoryEventBus):
    """An in-process bus that decouples publishing from handling via a queue.

    ``publish`` enqueues the event and returns immediately; a background consumer
    drains the queue and dispatches to handlers. This gives ``QUEUED`` semantics
    without introducing a broker. Call :meth:`start` before publishing and
    :meth:`stop` to drain and shut down the consumer.
    """

    def __init__(
        self,
        on_error: Callable[[Event, Exception], Awaitable[None]] | None = None,
        *,
        maxsize: int = 0,
    ) -> None:
        super().__init__(on_error=on_error, concurrency=Concurrency.QUEUED)
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=maxsize)
        self._consumer_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the background consumer task."""
        if self._consumer_task is None or self._consumer_task.done():
            self._consumer_task = asyncio.create_task(self._consume())

    async def stop(self) -> None:
        """Stop the consumer after draining queued events."""
        if self._consumer_task is not None:
            await self._queue.join()
            self._consumer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._consumer_task
            self._consumer_task = None

    async def publish(self, event: Event) -> None:
        """Enqueue ``event`` for asynchronous dispatch (fire-and-forget)."""
        event = self._attach_context(event)
        await self._queue.put(event)

    async def _consume(self) -> None:
        while True:
            event = await self._queue.get()
            try:
                await super().publish(event)
            finally:
                self._queue.task_done()


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
    "InMemoryEventBus",
    "QueuedEventBus",
    "RetryPolicy",
    "event_handler",
]
