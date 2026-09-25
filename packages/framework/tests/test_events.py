"""Tests for the framework event contracts."""

from dataclasses import dataclass

from power_framework.events import (Concurrency, DomainEvent, Event,
                                    HandlerSpec, RetryPolicy, event_handler)
from power_framework.exceptions import InfrastructureError


@dataclass(frozen=True, kw_only=True)
class _BusinessEvent(DomainEvent):
    value: str


def test_event_has_identity_and_timestamp():
    event = Event()
    assert event.event_id
    assert event.timestamp is not None


def test_domain_event_is_an_event():
    event = _BusinessEvent(value="hello")
    assert isinstance(event, Event)


def test_concurrency_modes():
    assert [mode.value for mode in Concurrency] == ["sequential", "concurrent", "queued"]


def test_retry_policy_defaults_to_infrastructure_errors():
    policy = RetryPolicy()
    assert policy.max_attempts == 3
    assert policy.delay_seconds == 0.0
    assert policy.retry_on == (InfrastructureError,)


def test_handler_decorator_returns_a_handler_spec():
    @event_handler(Event, concurrency=Concurrency.CONCURRENT, retry=RetryPolicy(max_attempts=2))
    async def on_event(event: Event) -> None:
        ...

    assert isinstance(on_event, HandlerSpec)
    assert on_event.event_type is Event
    assert on_event.concurrency is Concurrency.CONCURRENT
    assert on_event.retry is not None
    assert on_event.retry.max_attempts == 2
