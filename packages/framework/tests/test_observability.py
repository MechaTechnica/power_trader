"""Tests for the framework observability contracts (correlation + in-memory fakes)."""

import asyncio

from power_framework.observability import (
    AuditEvent,
    InMemoryAuditSink,
    InMemoryMetrics,
    InMemoryTracer,
    correlation_scope,
    current_correlation_id,
    current_trace_id,
)


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
