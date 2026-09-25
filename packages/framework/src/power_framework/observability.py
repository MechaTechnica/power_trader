"""Framework observability contracts.

This module owns the *contracts* (protocols and value types) for structured
logging, metrics, tracing, and audit — plus the in-memory fakes used by the test
harness and the ambient correlation/trace context they all share.

Concrete production implementations (the JSON ``StructuredLogger``, the
human-readable ``TerminalLogger``, the OpenTelemetry-backed tracer, and the
:func:`redact` engine) live in ``power_core.observability``. The framework stays
a pure contract layer so it can remain a dependency of everything without
dragging implementation details (stdlib logging, OTel adapters) into every
consumer.

The guarantee the framework adds is *automatic context injection*: when an
application logs a structured event::

    logger.info("order_submitted", order_id=order.id, instrument=order.instrument)

the framework automatically attaches the standard fields ``service``,
``environment``, ``version``, ``timestamp``, ``correlation_id``, and
``trace_id`` (pulled from the ambient correlation/trace context).

Sensitive data
--------------
``Secret``/``Redacted`` mark values that must never reach logs or telemetry.
The actual redaction rules (sensitive-key denylist and recursive traversal) are
implemented by ``power_core.observability.redact``, applied automatically before
emission by the concrete loggers.

Audit vs. operational logging
-----------------------------
Operational logs and compliance audit records are *different concerns*. The
framework keeps them separate: :class:`Logger` is for operational telemetry,
while :class:`AuditSink` records immutable, tamper-evident audit events.
"""

from __future__ import annotations

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
_current_span_var: ContextVar[Any] = ContextVar("current_span", default=None)


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
# Sensitive data markers
# ---------------------------------------------------------------------------

#: Placeholder substituted for redacted values by the concrete loggers.
_REDACTED = "[REDACTED]"


class Secret:
    """A value that must never be serialized into logs or telemetry.

    Wrap a secret (token, password, key) in :class:`Secret` (or
    :class:`Redacted`) so the framework redacts it automatically rather than
    relying on every caller to remember.
    """

    __slots__ = ("_value",)

    def __init__(self, value: Any) -> None:
        self._value = value

    def __repr__(self) -> str:
        return _REDACTED


class Redacted(Secret):
    """A :class:`Secret` that is replaced by ``[REDACTED]`` when serialized."""


# ---------------------------------------------------------------------------
# Structured logging contract
# ---------------------------------------------------------------------------


class Logger(Protocol):
    """A structured logger whose context is injected by the framework."""

    def debug(self, event: str, **fields: Any) -> None: ...

    def info(self, event: str, **fields: Any) -> None: ...

    def warning(self, event: str, **fields: Any) -> None: ...

    def error(self, event: str, **fields: Any) -> None: ...

    def audit(self, event: str, **fields: Any) -> None: ...


class TerminalLogger(Protocol):
    """A human-readable logger for interactive console output.

    The operator-facing counterpart to :class:`Logger` (structured JSON for
    permanent storage). It emits plain, readable lines rather than the JSON
    envelope, and has no ``audit`` method because compliance audit records go to
    a dedicated :class:`AuditSink`.
    """

    def debug(self, event: str, **fields: Any) -> None: ...

    def info(self, event: str, **fields: Any) -> None: ...

    def warning(self, event: str, **fields: Any) -> None: ...

    def error(self, event: str, **fields: Any) -> None: ...


# ---------------------------------------------------------------------------
# Audit (separate from operational logging)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuditEvent:
    """An immutable, compliance-grade audit record.

    Audit records are distinct from operational logs: they carry actor identity,
    action, target, and result, and are intended for a tamper-evident,
    access-controlled sink.
    """

    action: str
    actor: str | None = None
    target: str | None = None
    result: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, Any] = field(default_factory=dict)


class AuditSink(Protocol):
    """A sink for compliance audit records (separate from operational logs)."""

    async def record(self, event: AuditEvent) -> None:
        """Persist ``event`` to the audit trail."""
        ...


class InMemoryAuditSink:
    """A process-local audit sink for testing/single-node use."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    async def record(self, event: AuditEvent) -> None:
        self._events.append(event)

    @property
    def events(self) -> list[AuditEvent]:
        return list(self._events)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class Metrics(Protocol):
    """A minimal metrics surface (counters, gauges, histograms)."""

    def increment(self, name: str, value: int = 1, **labels: Any) -> None: ...

    def gauge(self, name: str, value: float, **labels: Any) -> None: ...

    def histogram(self, name: str, value: float, **labels: Any) -> None: ...


class InMemoryMetrics:
    """A process-local metrics store for testing/single-node use.

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

    Usable as a context manager to bind the ambient trace ID and current span
    for its duration::

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
    _trace_token: Any = None
    _span_token: Any = None

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def end(self) -> None:
        if self.end_time is None:
            self.end_time = time.monotonic()

    def __enter__(self) -> Span:
        self._trace_token = _trace_id_var.set(self.trace_id)
        self._span_token = _current_span_var.set(self)
        return self

    def __exit__(self, *exc: Any) -> None:
        self.end()
        if self._trace_token is not None:
            _trace_id_var.reset(self._trace_token)
            self._trace_token = None
        if self._span_token is not None:
            _current_span_var.reset(self._span_token)
            self._span_token = None


class Tracer(Protocol):
    """Creates spans for distributed tracing."""

    def start_span(self, name: str, **attributes: Any) -> Span: ...


class InMemoryTracer:
    """A process-local tracer that records spans and propagates trace IDs.

    The trace ID is taken from the ambient context when present, otherwise a
    fresh one is minted, keeping spans grouped under the same trace. The current
    span is tracked via a :class:`ContextVar`, so concurrent tasks each see their
    own parent span rather than a shared process-global one.
    """

    def __init__(self) -> None:
        self._spans: list[Span] = []

    def start_span(self, name: str, **attributes: Any) -> Span:
        trace_id = current_trace_id() or str(uuid.uuid4())
        parent = _current_span_var.get()
        span = Span(
            name=name,
            trace_id=trace_id,
            parent_id=parent.span_id if parent is not None else None,
            attributes=dict(attributes),
        )
        self._spans.append(span)
        return span

    @property
    def spans(self) -> list[Span]:
        """All spans started by this tracer, in creation order."""
        return list(self._spans)


__all__ = [
    "AuditEvent",
    "AuditSink",
    "InMemoryAuditSink",
    "InMemoryMetrics",
    "InMemoryTracer",
    "Logger",
    "Metrics",
    "Redacted",
    "Secret",
    "Span",
    "TerminalLogger",
    "Tracer",
    "correlation_scope",
    "current_correlation_id",
    "current_trace_id",
]
