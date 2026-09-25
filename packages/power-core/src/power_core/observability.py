"""Concrete observability implementations for the framework contracts.

``power_framework.observability`` declares the contracts (``Logger``, ``Metrics``,
``Tracer``, ``AuditSink`` and their value types). This module provides the real
production implementations:

- :class:`StructuredLogger` — emits one JSON object per event via stdlib logging.
- :class:`TerminalLogger` — human-readable console output.
- :class:`OpenTelemetryTracer` — delegates to OpenTelemetry when installed,
  falling back to the in-memory tracer otherwise.
- :func:`redact` — the sensitive-field redaction engine used by both loggers.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any, Self

from power_framework.observability import (InMemoryTracer, Secret, Span,
                                           current_correlation_id,
                                           current_trace_id)

# OpenTelemetry is an optional dependency: import it lazily at module scope so
# the runtime runs without it, but adapts to the existing OTel stack when present.
try:
    from opentelemetry import trace as _otel_trace
except ImportError:  # pragma: no cover - optional dependency
    _otel_trace = None

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


def redact(value: Any, *, key: str | None = None) -> Any:
    """Recursively redact sensitive values and keys.

    - :class:`~power_framework.observability.Secret` /
      :class:`~power_framework.observability.Redacted` values become ``[REDACTED]``.
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
        # ``AuditSink`` for compliance-grade audit records.
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
# Tracing
# ---------------------------------------------------------------------------


class OpenTelemetryTracer:
    """A :class:`Tracer` that delegates to OpenTelemetry when installed.

    If the ``opentelemetry-api`` package is available, spans are exported through
    the ambient OpenTelemetry tracer (so the framework adapts to the existing
    observability stack). Otherwise it falls back to the in-memory tracer,
    keeping the runtime runnable without the dependency.
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

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: Any) -> None:
        self._span.end()


__all__ = [
    "OpenTelemetryTracer",
    "StructuredLogger",
    "TerminalLogger",
    "redact",
]
