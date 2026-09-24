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

Sensitive data
--------------
Logging arbitrary fields is convenient but dangerous. The framework provides
:class:`Secret` and :class:`Redacted` wrappers plus automatic redaction of
sensitive keys (``token``, ``password``, ``api_key``, ...) so that secrets never
leak into operational logs::

    logger.info("request", token=Redacted(token), customer=customer)

Audit vs. operational logging
-----------------------------
Operational logs and compliance audit records are *different concerns*. The
framework keeps them separate: :class:`Logger` is for operational telemetry,
while :class:`AuditSink` records immutable, tamper-evident audit events.
"""

from __future__ import annotations

import json
import logging
import sys
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

# OpenTelemetry is an optional dependency: import it lazily at module scope so
# the framework runs without it, but adapts to the bank's OTel stack when present.
try:
    from opentelemetry import trace as _otel_trace  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency
    _otel_trace = None  # type: ignore[assignment]

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
# Sensitive data / redaction
# ---------------------------------------------------------------------------

#: Field names that are always redacted when serialized into logs/telemetry.
_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "passwd",
        "token",
        "secret",
        "api_key",
        "apikey",
        "authorization",
        "credential",
        "credentials",
        "private_key",
        "access_key",
        "connection_string",
        "cookie",
        "session",
    }
)

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


def redact(value: Any, *, key: str | None = None) -> Any:
    """Recursively redact sensitive values and keys.

    - :class:`Secret` / :class:`Redacted` values become ``[REDACTED]``.
    - Dict keys in the sensitive-key denylist become ``[REDACTED]``.
    - Lists/tuples/dicts are traversed recursively.

    This is applied automatically by :class:`StructuredLogger` before emission.
    """
    if isinstance(value, Secret):
        return _REDACTED
    if key is not None and key.lower() in _SENSITIVE_KEYS:
        return _REDACTED
    if isinstance(value, dict):
        return {k: redact(v, key=k) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    return value


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
    ``correlation_id``, and ``trace_id``. Sensitive fields are redacted before
    serialization (see :func:`redact`).
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
            **redact(fields),
        }
        self._logger.log(level, json.dumps(record, default=str))

    def log(self, event: str, *, level: int = logging.INFO, **fields: Any) -> None:
        """Emit a structured event at an explicit level (defaults to INFO).

        This is the generic entry point for permanent-storage records::

            structured_logger.log("test")
            structured_logger.log("order_rejected", level=logging.ERROR, order_id=42)

        It emits the same JSON envelope (timestamp, service, environment, version,
        level, event, correlation/trace IDs, and redacted fields) as the
        ``debug``/``info``/``warning``/``error`` helpers.
        """
        self._emit(level, event, fields)

    def debug(self, event: str, **fields: Any) -> None:
        self._emit(logging.DEBUG, event, fields)

    def info(self, event: str, **fields: Any) -> None:
        self._emit(logging.INFO, event, fields)

    def warning(self, event: str, **fields: Any) -> None:
        self._emit(logging.WARNING, event, fields)

    def error(self, event: str, **fields: Any) -> None:
        self._emit(logging.ERROR, event, fields)

    def audit(self, event: str, **fields: Any) -> None:
        # Convenience bridge to operational logging. Prefer a dedicated
        # :class:`AuditSink` for compliance-grade audit records.
        self._emit(logging.INFO, f"audit.{event}", fields)


#: Level prefix printed for non-INFO records; INFO is printed bare so the
#: operator sees exactly the message.
_LEVEL_PREFIX = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "",
    logging.WARNING: "WARNING",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRITICAL",
}


class TerminalLogger:
    """A human-readable logger for interactive terminal output.

    Emits plain, readable lines (the event name plus any fields) rather than the
    JSON envelope produced by :class:`StructuredLogger`. It is the
    operator-facing counterpart to the structured logger: use :class:`TerminalLogger`
    for the console and :class:`StructuredLogger` for machine-readable records
    sent to permanent storage (e.g. Cosmos DB).

    Because terminal output is for humans, the record is printed *as-is* — an
    INFO ``application_started`` is shown as just ``application_started``, with
    no timestamp/service/context boilerplate. Sensitive fields are still redacted
    so secrets never reach the console.
    """

    def __init__(self, *, stream: Any = None) -> None:
        self._stream = stream or sys.stderr

    def _emit(self, level: int, event: str, fields: dict[str, Any]) -> None:
        parts: list[str] = []
        prefix = _LEVEL_PREFIX.get(level, "")
        if prefix:
            parts.append(prefix)
        parts.append(event)
        if fields:
            rendered = " ".join(f"{k}={v!r}" for k, v in redact(fields).items())
            parts.append(rendered)
        print(" ".join(parts), file=self._stream)

    def debug(self, event: str, **fields: Any) -> None:
        self._emit(logging.DEBUG, event, fields)

    def info(self, event: str, **fields: Any) -> None:
        self._emit(logging.INFO, event, fields)

    def warning(self, event: str, **fields: Any) -> None:
        self._emit(logging.WARNING, event, fields)

    def error(self, event: str, **fields: Any) -> None:
        self._emit(logging.ERROR, event, fields)


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


class OpenTelemetryTracer:
    """A :class:`Tracer` that delegates to OpenTelemetry when installed.

    If the ``opentelemetry-api`` package is available, spans are exported through
    the ambient OpenTelemetry tracer (so the framework adapts to the bank's
    existing observability stack). Otherwise it falls back to the in-memory
    tracer, keeping the framework runnable without the dependency.
    """

    def __init__(self, service_name: str = "power-framework") -> None:
        self._service_name = service_name
        self._otel_tracer: Any = None
        self._fallback = InMemoryTracer()
        if _otel_trace is not None:
            self._otel_tracer = _otel_trace.get_tracer(service_name)

    def start_span(self, name: str, **attributes: Any) -> Span:
        if self._otel_tracer is None:
            return self._fallback.start_span(name, **attributes)
        otel_span = self._otel_tracer.start_span(name, attributes=attributes)
        return _OtelSpanAdapter(otel_span)  # type: ignore[return-value]


class _OtelSpanAdapter:
    """Adapts an OpenTelemetry span to the framework's :class:`Span` interface."""

    def __init__(self, span: Any) -> None:
        self._span = span

    def set_attribute(self, key: str, value: Any) -> None:
        self._span.set_attribute(key, value)

    def end(self) -> None:
        self._span.end()

    def __enter__(self) -> _OtelSpanAdapter:
        return self

    def __exit__(self, *exc: Any) -> None:
        self._span.end()


__all__ = [
    "AuditEvent",
    "AuditSink",
    "InMemoryAuditSink",
    "InMemoryMetrics",
    "InMemoryTracer",
    "Logger",
    "Metrics",
    "OpenTelemetryTracer",
    "Redacted",
    "Secret",
    "Span",
    "StructuredLogger",
    "TerminalLogger",
    "Tracer",
    "correlation_scope",
    "current_correlation_id",
    "current_trace_id",
    "redact",
]
