"""Tests for the framework observability capability."""

import json
import logging

from power_framework.observability import (InMemoryMetrics, InMemoryTracer,
                                           StructuredLogger, correlation_scope,
                                           current_correlation_id,
                                           current_trace_id)


def test_structured_logger_injects_context(caplog):
    logger = StructuredLogger(
        service="test-svc", environment="production", version="1.2.3"
    )

    with caplog.at_level(logging.INFO):
        with correlation_scope("corr-1", "trace-1"):
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
    with correlation_scope(trace_id="trace-123"):
        with tracer.start_span("place_order", instrument="AAPL") as span:
            assert current_trace_id() == "trace-123"
            assert span.trace_id == "trace-123"
            span.set_attribute("quantity", 10)

    assert len(tracer.spans) == 1
    recorded = tracer.spans[0]
    assert recorded.name == "place_order"
    assert recorded.attributes["instrument"] == "AAPL"
    assert recorded.attributes["quantity"] == 10
    assert recorded.end_time is not None
