"""Tests for the framework observability capability."""

import asyncio
import json
import logging
from io import StringIO

from power_framework.observability import (
    AuditEvent,
    InMemoryAuditSink,
    InMemoryMetrics,
    InMemoryTracer,
    Redacted,
    Secret,
    StructuredLogger,
    TerminalLogger,
    correlation_scope,
    current_correlation_id,
    current_trace_id,
    redact,
)


def test_structured_logger_injects_context(caplog):
    logger = StructuredLogger(service="test-svc", environment="production", version="1.2.3")

    with caplog.at_level(logging.INFO), correlation_scope("corr-1", "trace-1"):
        logger.info("order_submitted", order_id="42", instrument="AAPL")

    assert len(caplog.records) == 1
    payload = json.loads(caplog.records[0].getMessage())
    assert payload["service"] == "test-svc"
    assert payload["environment"] == "production"
    assert payload["version"] == "1.2.3"
    assert payload["event"] == "order_submitted"
    assert payload["correlation_id"] == "corr-1"
    assert payload["trace_id"] == "trace-1"
    assert payload["order_id"] == "42"
    assert payload["instrument"] == "AAPL"
    assert "timestamp" in payload


def test_terminal_logger_prints_plain_message():
    stream = StringIO()
    logger = TerminalLogger(stream=stream)

    logger.info("application_started")

    assert stream.getvalue() == "application_started\n"


def test_terminal_logger_adds_level_prefix_for_non_info():
    stream = StringIO()
    logger = TerminalLogger(stream=stream)

    logger.warning("latency_high", latency_ms=150)
    logger.error("connection_lost")

    lines = stream.getvalue().splitlines()
    assert lines[0] == "WARNING latency_high latency_ms=150"
    assert lines[1] == "ERROR connection_lost"


def test_terminal_logger_redacts_sensitive_fields():
    stream = StringIO()
    logger = TerminalLogger(stream=stream)

    logger.info("request", token=Secret("s3cret"), customer="alice")

    assert stream.getvalue() == "request token='[REDACTED]' customer='alice'\n"


def test_structured_logger_log_method_emits_envelope(caplog):
    logger = StructuredLogger(service="svc", environment="dev")

    with caplog.at_level(logging.INFO):
        logger.log("test")

    payload = json.loads(caplog.records[0].getMessage())
    assert payload["event"] == "test"
    assert payload["level"] == "INFO"
    assert payload["service"] == "svc"


def test_audit_event_is_prefixed(caplog):
    logger = StructuredLogger(service="s", environment="dev")

    with caplog.at_level(logging.INFO):
        logger.audit("trade_executed", order_id="7")

    payload = json.loads(caplog.records[0].getMessage())
    assert payload["event"] == "audit.trade_executed"
    assert payload["order_id"] == "7"


def test_correlation_scope_sets_and_resets_ids():
    assert current_correlation_id() is None
    assert current_trace_id() is None

    with correlation_scope("cid", "tid"):
        assert current_correlation_id() == "cid"
        assert current_trace_id() == "tid"

    assert current_correlation_id() is None
    assert current_trace_id() is None


def test_in_memory_metrics_records_values():
    metrics = InMemoryMetrics()
    metrics.increment("orders", 2, instrument="AAPL")
    metrics.increment("orders", 1, instrument="AAPL")
    metrics.gauge("open_positions", 5)
    metrics.histogram("latency_ms", 12.5)

    assert metrics.counter_value("orders", instrument="AAPL") == 3
    assert metrics.gauge_value("open_positions") == 5
    assert metrics.histogram_values("latency_ms") == [12.5]


def test_tracer_records_span_and_propagates_trace_id():
    tracer = InMemoryTracer()
    with (
        correlation_scope(trace_id="trace-123"),
        tracer.start_span("place_order", instrument="AAPL") as span,
    ):
        assert current_trace_id() == "trace-123"
        assert span.trace_id == "trace-123"
        span.set_attribute("quantity", 10)

    assert len(tracer.spans) == 1
    recorded = tracer.spans[0]
    assert recorded.name == "place_order"
    assert recorded.attributes["instrument"] == "AAPL"
    assert recorded.attributes["quantity"] == 10
    assert recorded.end_time is not None


def test_redact_hides_secrets_and_sensitive_keys():
    assert redact(Secret("abc")) == "[REDACTED]"
    assert redact(Redacted("abc")) == "[REDACTED]"
    assert redact({"token": "abc", "ok": "visible"}) == {
        "token": "[REDACTED]",
        "ok": "visible",
    }
    assert redact({"nested": {"api_key": "x"}}) == {"nested": {"api_key": "[REDACTED]"}}


def test_structured_logger_redacts_sensitive_fields(caplog):
    logger = StructuredLogger(service="s", environment="dev")

    with caplog.at_level(logging.INFO):
        logger.info("request", token=Secret("secret-token"), customer="alice")

    payload = json.loads(caplog.records[0].getMessage())
    assert payload["token"] == "[REDACTED]"
    assert payload["customer"] == "alice"


async def test_audit_sink_records_immutable_events():
    sink = InMemoryAuditSink()

    await sink.record(AuditEvent(action="order.submitted", actor="trader-1"))

    assert len(sink.events) == 1
    assert sink.events[0].action == "order.submitted"
    assert sink.events[0].actor == "trader-1"


async def test_tracer_uses_contextvar_not_shared_state():
    tracer = InMemoryTracer()

    async def make_span(name: str) -> None:
        with tracer.start_span(name) as span:
            await asyncio.sleep(0.01)
            assert span.parent_id is None  # each task sees no parent

    await asyncio.gather(make_span("a"), make_span("b"))

    assert len(tracer.spans) == 2
    # No span incorrectly inherited another task's span as parent.
    assert all(span.parent_id is None for span in tracer.spans)
