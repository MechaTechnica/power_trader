"""Tests for the framework event bus capability."""

import asyncio
from dataclasses import dataclass

import pytest
from power_framework.events import (Concurrency, DomainEvent, Event,
                                    InMemoryEventBus, QueuedEventBus,
                                    RetryPolicy, event_handler)
from power_framework.exceptions import InfrastructureError
from power_framework.observability import correlation_scope


@dataclass(frozen=True, kw_only=True)
class _BusinessEvent(DomainEvent):
    value: str


class _RecordingHandler:
    def __init__(self) -> None:
        self.handled: list[Event] = []

    async def handle(self, event: Event) -> None:
        self.handled.append(event)


class _RaisingHandler:
    async def handle(self, event: Event) -> None:
        raise RuntimeError("boom")


async def test_bus_dispatches_to_matching_handler():
    bus = InMemoryEventBus()
    handler = _RecordingHandler()
    bus.subscribe(Event, handler)

    event = Event()
    await bus.publish(event)

    assert handler.handled == [event]


async def test_bus_matches_subclasses_of_subscribed_type():
    bus = InMemoryEventBus()
    handler = _RecordingHandler()
    bus.subscribe(DomainEvent, handler)

    event = _BusinessEvent(value="hello")
    await bus.publish(event)

    assert handler.handled == [event]


async def test_bus_stamps_ambient_context_onto_event():
    bus = InMemoryEventBus()
    handler = _RecordingHandler()
    bus.subscribe(Event, handler)

    with correlation_scope(correlation_id="cid-1", trace_id="trace-1"):
        await bus.publish(Event())

    published = handler.handled[0]
    assert published.correlation_id == "cid-1"
    assert published.trace_id == "trace-1"


async def test_handler_failure_is_isolated_and_routed_to_on_error():
    errors: list[tuple[Event, Exception]] = []

    async def on_error(event: Event, error: Exception) -> None:
        errors.append((event, error))

    bus = InMemoryEventBus(on_error=on_error)
    ok_handler = _RecordingHandler()
    bus.subscribe(Event, _RaisingHandler())
    bus.subscribe(Event, ok_handler)

    event = Event()
    await bus.publish(event)

    assert len(errors) == 1
    assert isinstance(errors[0][1], RuntimeError)
    # The failing handler did not prevent the healthy handler from running.
    assert ok_handler.handled == [event]


async def test_handler_failure_re_raises_without_on_error():
    bus = InMemoryEventBus()
    bus.subscribe(Event, _RaisingHandler())

    with pytest.raises(RuntimeError, match="boom"):
        await bus.publish(Event())


def test_event_has_identity_and_timestamp():
    event = Event()
    assert event.event_id
    assert event.timestamp is not None


async def test_concurrent_bus_runs_handlers_together():
    bus = InMemoryEventBus(concurrency=Concurrency.CONCURRENT)
    order: list[str] = []

    class SlowHandler:
        def __init__(self, name: str) -> None:
            self._name = name

        async def handle(self, event: Event) -> None:
            await asyncio.sleep(0.02)
            order.append(self._name)

    bus.subscribe(Event, SlowHandler("a"))
    bus.subscribe(Event, SlowHandler("b"))

    await bus.publish(Event())

    # Both handlers ran (concurrently), so both recorded.
    assert set(order) == {"a", "b"}


async def test_queued_bus_decouples_publish_from_handling():
    bus = QueuedEventBus()
    handled: list[Event] = []

    class Recording:
        async def handle(self, event: Event) -> None:
            handled.append(event)

    bus.subscribe(Event, Recording())
    await bus.start()

    await bus.publish(Event())
    await bus.stop()

    assert len(handled) == 1


async def test_handler_decorator_registers_with_retry_policy():
    bus = InMemoryEventBus()
    attempts = {"n": 0}

    @event_handler(Event, retry=RetryPolicy(max_attempts=3))
    async def on_event(event: Event) -> None:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise InfrastructureError("transient")

    bus.register(on_event)
    await bus.publish(Event())

    assert attempts["n"] == 3
