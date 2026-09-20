"""Cross-cutting concerns via interceptors (aspect-oriented decorators).

The framework separates business logic from cross-cutting concerns (retry,
observability, audit, transactions) using an :class:`Interceptor` abstraction.
Interceptors are applied *externally* to a function via :func:`intercept` (or the
convenience factories :func:`retry`, :func:`observed`, :func:`audited`), so the
business function itself stays unaware of them::

    @observed(logger)
    async def process_payment(order_id: str) -> None:
        ...

    @retry(max_attempts=3)
    async def publish(event: DomainEvent) -> None:
        ...

    @intercept(RetryInterceptor(max_attempts=5), ObserveInterceptor(logger))
    async def reconcile() -> None:
        ...

Adding a new cross-cutting concern (e.g. ``@transactional``) means implementing
one more :class:`Interceptor` and applying it — never editing the business code
it decorates.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import time
from typing import TYPE_CHECKING, Any, ParamSpec, Protocol, TypeVar, cast

from power_framework.exceptions import InfrastructureError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine, Sequence

    from power_framework.observability import Logger

P = ParamSpec("P")
R = TypeVar("R")


class Interceptor(Protocol):
    """A cross-cutting behavior applied around a single function invocation.

    Implementations receive the function ``name`` and the next callable in the
    chain, plus the invocation arguments, and must forward to ``proceed`` — once
    for normal interceptors, multiple times for retry-like interceptors.
    """

    async def around(
        self,
        name: str,
        proceed: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any: ...


def _compose(
    func: Callable[..., Any],
    interceptors: Sequence[Interceptor],
) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Build the interceptor chain around ``func`` (innermost → outermost)."""
    name = getattr(func, "__name__", "<unknown>")

    async def invoke(*args: Any, **kwargs: Any) -> Any:
        result = func(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    handler: Callable[..., Coroutine[Any, Any, Any]] = invoke
    for interceptor in reversed(interceptors):
        current = handler

        async def wrapped(
            *args: Any,
            _interceptor: Interceptor = interceptor,
            _next: Callable[..., Coroutine[Any, Any, Any]] = current,
            **kwargs: Any,
        ) -> Any:
            return await _interceptor.around(name, _next, *args, **kwargs)

        handler = wrapped

    return handler


def intercept(
    *interceptors: Interceptor,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Apply one or more interceptors around a function.

    The decorated function keeps its original name/signature and its sync or
    async nature; the interceptors run without the business function knowing
    about them.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        chain = _compose(func, interceptors)

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                return cast("R", await chain(*args, **kwargs))

            return cast("Callable[P, R]", async_wrapper)

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return cast("R", asyncio.run(chain(*args, **kwargs)))

        return cast("Callable[P, R]", sync_wrapper)

    return decorator


class RetryInterceptor:
    """Retry the invocation on transient (retryable) failures.

    By default it retries :class:`~power_framework.exceptions.InfrastructureError`
    (and subclasses), which the framework classifies as transient. ``retry_on``
    narrows or widens the set of exceptions that trigger a retry.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        *,
        delay_seconds: float = 0.0,
        retry_on: type[BaseException] | tuple[type[BaseException], ...] = InfrastructureError,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self._max_attempts = max_attempts
        self._delay_seconds = delay_seconds
        self._retry_on = retry_on

    async def around(
        self,
        name: str,  # noqa: ARG002 - required by the Interceptor protocol
        proceed: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        attempts = 0
        while True:
            attempts += 1
            try:
                return await proceed(*args, **kwargs)
            except self._retry_on:
                if attempts >= self._max_attempts:
                    raise
                if self._delay_seconds > 0:
                    await asyncio.sleep(self._delay_seconds)


class ObserveInterceptor:
    """Measure and log the duration of each invocation.

    Duration is recorded even when the invocation raises, so observed functions
    contribute latency telemetry on both success and failure paths.
    """

    def __init__(self, logger: Logger | None = None) -> None:
        self._logger = logger

    async def around(
        self,
        name: str,
        proceed: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        started = time.monotonic()
        try:
            return await proceed(*args, **kwargs)
        finally:
            if self._logger is not None:
                duration_ms = round((time.monotonic() - started) * 1000, 3)
                self._logger.debug(
                    "function_observed", function=name, duration_ms=duration_ms
                )


class AuditInterceptor:
    """Emit an audit event on each invocation (entry and completion)."""

    def __init__(self, logger: Logger | None = None) -> None:
        self._logger = logger

    async def around(
        self,
        name: str,
        proceed: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if self._logger is not None:
            self._logger.audit("function_invoked", function=name)
        result = await proceed(*args, **kwargs)
        if self._logger is not None:
            self._logger.audit("function_completed", function=name)
        return result


def retry(
    max_attempts: int = 3,
    *,
    delay_seconds: float = 0.0,
    retry_on: type[BaseException] | tuple[type[BaseException], ...] = InfrastructureError,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorate a function to retry transient failures.

    Usage::

        @retry(max_attempts=3)
        async def publish(event: DomainEvent) -> None:
            ...
    """
    return intercept(
        RetryInterceptor(
            max_attempts, delay_seconds=delay_seconds, retry_on=retry_on
        )
    )


def observed(logger: Logger | None = None) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorate a function to record its invocation latency.

    Usage::

        @observed(logger)
        async def process_payment(order_id: str) -> None:
            ...
    """
    return intercept(ObserveInterceptor(logger))


def audited(logger: Logger | None = None) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorate a function to emit an audit trail.

    Usage::

        @audited(logger)
        async def transfer(amount: Decimal) -> None:
            ...
    """
    return intercept(AuditInterceptor(logger))


__all__ = [
    "AuditInterceptor",
    "Interceptor",
    "ObserveInterceptor",
    "RetryInterceptor",
    "audited",
    "intercept",
    "observed",
    "retry",
]
