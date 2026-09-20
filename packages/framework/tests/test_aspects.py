"""Tests for the framework interceptor/aspect capability."""

from typing import Any

import pytest

from power_framework.aspects import (
    ObserveInterceptor,
    RetryInterceptor,
    audited,
    intercept,
    observed,
    retry,
)
from power_framework.exceptions import InfrastructureError


class _FakeLogger:
    """A minimal ``Logger`` double that records structured events."""

    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict[str, Any]]] = []

    def _record(self, level: str, event: str, fields: dict[str, Any]) -> None:
        self.events.append((level, event, fields))

    def debug(self, event: str, **fields: Any) -> None:
        self._record("debug", event, fields)

    def info(self, event: str, **fields: Any) -> None:
        self._record("info", event, fields)

    def warning(self, event: str, **fields: Any) -> None:
        self._record("warning", event, fields)

    def error(self, event: str, **fields: Any) -> None:
        self._record("error", event, fields)

    def audit(self, event: str, **fields: Any) -> None:
        self._record("audit", event, fields)


def test_intercept_preserves_sync_function():
    calls: list[tuple[int, int]] = []

    @intercept(ObserveInterceptor())
    def add(a: int, b: int) -> int:
        calls.append((a, b))
        return a + b

    assert add(2, 3) == 5
    assert calls == [(2, 3)]


async def test_intercept_preserves_async_function():
    @intercept(ObserveInterceptor())
    async def greet(name: str) -> str:
        return f"hello {name}"

    assert await greet("world") == "hello world"


async def test_retry_succeeds_after_transient_failures():
    attempts = {"n": 0}

    @retry(max_attempts=3)
    async def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise InfrastructureError("transient")
        return "ok"

    assert await flaky() == "ok"
    assert attempts["n"] == 3


async def test_retry_gives_up_after_max_attempts():
    calls = {"n": 0}

    @retry(max_attempts=2)
    async def always_fail() -> None:
        calls["n"] += 1
        raise InfrastructureError("still down")

    with pytest.raises(InfrastructureError):
        await always_fail()
    assert calls["n"] == 2


async def test_retry_does_not_retry_non_retryable_errors():
    calls = {"n": 0}

    @retry(max_attempts=3)
    async def invalid() -> None:
        calls["n"] += 1
        raise ValueError("not transient")

    with pytest.raises(ValueError):
        await invalid()
    assert calls["n"] == 1


async def test_retry_honours_custom_retry_on():
    calls = {"n": 0}

    @retry(max_attempts=3, retry_on=ValueError)
    async def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 2:
            raise ValueError("custom retryable")
        return "done"

    assert await flaky() == "done"
    assert calls["n"] == 2


async def test_observed_logs_duration():
    logger = _FakeLogger()

    @observed(logger)
    async def work() -> str:
        return "done"

    assert await work() == "done"
    assert any(event == "function_observed" for _, event, _ in logger.events)
    observed_event = next(e for e in logger.events if e[1] == "function_observed")
    assert observed_event[2]["function"] == "work"
    assert "duration_ms" in observed_event[2]


async def test_audited_emits_entry_and_completion_events():
    logger = _FakeLogger()

    @audited(logger)
    async def transfer() -> None:
        return None

    await transfer()

    names = [event for _, event, _ in logger.events]
    assert names == ["function_invoked", "function_completed"]


async def test_interceptors_compose():
    logger = _FakeLogger()

    @intercept(RetryInterceptor(max_attempts=2), ObserveInterceptor(logger))
    async def flaky() -> str:
        raise InfrastructureError("down")

    with pytest.raises(InfrastructureError):
        await flaky()

    # The observe interceptor still recorded the (failing) invocations.
    assert any(event == "function_observed" for _, event, _ in logger.events)
