"""In-process event transport implementations.

``power_framework.events`` defines the *contracts* (``Event``, ``EventBus``,
``EventHandler``, ``HandlerSpec``, ``Concurrency``, and ``RetryPolicy``). This
module provides the concrete in-process transports that the runtime registers
as the default ``EventBus``:

- :class:`InMemoryEventBus` — process-local, non-durable, fan-out dispatch with
  sequential/concurrent modes, error isolation, and retry support.
- :class:`QueuedEventBus` — decouples publishing from handling through an
  in-process queue drained by a background consumer.

Durable transports (Kafka, message queues) would live here as further
implementations of the ``power_framework.events.EventBus`` contract.
"""

import asyncio
import contextlib
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import replace
from typing import Any

from power_framework.events import (Concurrency, Event, EventHandler,
                                    HandlerSpec)
from power_framework.observability import (current_correlation_id,
                                           current_trace_id)


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


__all__ = [
    "InMemoryEventBus",
    "QueuedEventBus",
]