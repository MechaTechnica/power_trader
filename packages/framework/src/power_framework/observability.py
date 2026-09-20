"""Framework observability capability.

Observability is a *framework* concern, not an application concern. This module
provides the shared vocabulary and default implementations for structured
logging, distributed tracing, metrics, and audit events, so every application
produces consistent telemetry without each team re-inventing the stack.

The key guarantee is *automatic context injection*: when an application logs a
structured event::

    logger.info("order_submitted", order_id=order.id, instrument=order.instrument)

the framework automatically attaches the standard fields ``service``,
``environment``, ``version``, ``timestamp``, ``correlation_id``, and
``trace_id`` (pulled from the ambient correlation/trace context).
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterator

# ---------------------------------------------------------------------------
# Correlation / trace context
# ---------------------------------------------------------------------------

_correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)


def current_correlation_id() -> str | None:
    """Return the ambient correlation ID, if any."""
    return _correlation_id_var.get()


def current_trace_id() -> str | None:
    """Return the ambient trace ID, if any."""
    return _trace_id_var.get()


@contextmanager
def correlation_scope(
    correlation_id: str | None = None,
    trace_id: str | None = None,
) -> Iterator[None]:
    """Set ambient correlation/trace IDs for the duration of the block.

    IDs default to fresh UUIDs when omitted, so a single request/message/job can
    propagate a shared identity through everything it touches.
    """
    cid = correlation_id or str(uuid.uuid4())
    tid = trace_id or str(uuid.uuid4())
    cid_token = _correlation_id_var.set(cid)
    tid_token = _trace_id_var.set(tid)
    try:
        yield
    finally:
        _correlation_id_var.reset(cid_token)
        _trace_id_var.reset(tid_token)


# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------


class Logger(Protocol):
    """A structured logger whose context is injected by the framework."""

    def debug(self, event: str, **fields: Any) -> None: ...

    def info(self, event: str, **fields: Any) -> None: ...

    def warning(self, event: str, **fields: Any) -> None: ...

    def error(self, event: str, **fields: Any) -> None: ...

    def audit(self, event: str, **fields: Any) -> None: ...


class StructuredLogger:
    """A ``Logger`` that emits one JSON object per event via stdlib logging.

    Every record is automatically decorated with the standard context:
    ``timestamp``, ``service``, ``environment``, ``version``, ``level``,
    ``correlation_id``, and ``trace_id``.
    """

    def __init__(
        self,
        *,
        service: str,
        environment: str,
        version: str = "unknown",
        logger: logging.Logger | None = None,
    ) -> None:
        self._service = service
        self._environment = environment
        self._version = version
        self._logger = logger or logging.getLogger(service)

    def _emit(self, level: int, event: str, fields: dict[str, Any]) -> None:
        record: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "service": self._service,
            "environment": self._environment,
            "version": self._version,
            "level": logging.getLevelName(level),
            "event": event,
            "correlation_id": current_correlation_id(),
            "trace_id": current_trace_id(),
            **fields,
        }
        self._logger.log(level, json.dumps(record, default=str))

    def debug(self, event: str, **fields: Any) -> None:
        self._emit(logging.DEBUG, event, fields)

    def info(self, event: str, **fields: Any) -> None:
        self._emit(logging.INFO, event, fields)

    def warning(self, event: str, **fields: Any) -> None:
        self._emit(logging.WARNING, event, fields)

    def error(self, event: str, **fields: Any) -> None:
        self._emit(logging.ERROR, event, fields)

    def audit(self, event: str, **fields: Any) -> None:
        # Audit events are informational but always recorded (compliance trail).
        self._emit(logging.INFO, f"audit.{event}", fields)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class Metrics(Protocol):
    """A minimal metrics surface (counters, gauges, histograms)."""

    def increment(self, name: str, value: int = 1, **labels: Any) -> None: ...

    def gauge(self, name: str, value: float, **labels: Any) -> None: ...

    def histogram(self, name: str, value: float, **labels: Any) -> None: ...


class InMemoryMetrics:
    """A thread-safe-free, process-local metrics store for testing/single-node use.

    Production deployments would swap this for a Prometheus/OTLP exporter, but
    the *shape* (names + labels) stays identical.
    """

    def __init__(self) -> None:
        self._counters: dict[tuple[Any, ...], int] = defaultdict(int)
        self._gauges: dict[tuple[Any, ...], float] = {}
        self._histograms: dict[tuple[Any, ...], list[float]] = defaultdict(list)

    @staticmethod
    def _key(name: str, labels: dict[str, Any]) -> tuple[Any, ...]:
        return (name, *sorted(labels.items()))

    def increment(self, name: str, value: int = 1, **labels: Any) -> None:
        self._counters[self._key(name, labels)] += value

    def gauge(self, name: str, value: float, **labels: Any) -> None:
        self._gauges[self._key(name, labels)] = value

    def histogram(self, name: str, value: float, **labels: Any) -> None:
        self._histograms[self._key(name, labels)].append(value)

    def counter_value(self, name: str, **labels: Any) -> int:
        return self._counters[self._key(name, labels)]

    def gauge_value(self, name: str, **labels: Any) -> float:
        return self._gauges[self._key(name, labels)]

    def histogram_values(self, name: str, **labels: Any) -> list[float]:
        return list(self._histograms[self._key(name, labels)])


# ---------------------------------------------------------------------------
# Tracing
# ---------------------------------------------------------------------------


@dataclass
class Span:
    """A single operation span.

    Usable as a context manager to bind the ambient trace ID for its duration::

        with tracer.start_span("place_order") as span:
            ...
    """

    name: str
    trace_id: str
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.monotonic)
    end_time: float | None = None
    _token: Any = None

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def end(self) -> None:
        if self.end_time is None:
            self.end_time = time.monotonic()

    def __enter__(self) -> Span:
        self._token = _trace_id_var.set(self.trace_id)
        return self

    def __exit__(self, *exc: Any) -> None:
        self.end()
        if self._token is not None:
            _trace_id_var.reset(self._token)
            self._token = None


class Tracer(Protocol):
    """Creates spans for distributed tracing."""

    def start_span(self, name: str, **attributes: Any) -> Span: ...


class InMemoryTracer:
    """A process-local tracer that records spans and propagates trace IDs.

    The trace ID is taken from the ambient context when present, otherwise a
    fresh one is minted, keeping spans grouped under the same trace.
    """

    def __init__(self) -> None:
        self._spans: list[Span] = []
        self._active: Span | None = None

    def start_span(self, name: str, **attributes: Any) -> Span:
        trace_id = current_trace_id() or str(uuid.uuid4())
        span = Span(
            name=name,
            trace_id=trace_id,
            parent_id=self._active.span_id if self._active else None,
            attributes=dict(attributes),
        )
        self._spans.append(span)
        self._active = span
        return span

    @property
    def spans(self) -> list[Span]:
        """All spans started by this tracer, in creation order."""
        return list(self._spans)


__all__ = [
    "InMemoryMetrics",
    "InMemoryTracer",
    "Logger",
    "Metrics",
    "Span",
    "StructuredLogger",
    "Tracer",
    "correlation_scope",
    "current_correlation_id",
    "current_trace_id",
]
