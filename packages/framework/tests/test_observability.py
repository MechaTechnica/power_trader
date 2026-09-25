"""Tests for the framework observability contracts (correlation + markers)."""

from power_framework.observability import (AuditEvent, Redacted, Secret,
                                           correlation_scope,
                                           current_correlation_id,
                                           current_span, current_trace_id)


def test_correlation_scope_sets_and_resets_ids():
    assert current_correlation_id() is None
    assert current_trace_id() is None
    assert current_span() is None

    with correlation_scope("cid", "tid"):
        assert current_correlation_id() == "cid"
        assert current_trace_id() == "tid"

    assert current_correlation_id() is None
    assert current_trace_id() is None


def test_secret_and_redacted_mark_sensitive_values():
    assert repr(Secret("s3cret")) == "[REDACTED]"
    assert repr(Redacted("s3cret")) == "[REDACTED]"

    # ``Redacted`` is a more specific ``Secret``.
    assert isinstance(Redacted("x"), Secret)


def test_audit_event_carries_identity_fields():
    event = AuditEvent(action="order.submitted", actor="trader-1", target="AAPL")
    assert event.action == "order.submitted"
    assert event.actor == "trader-1"
    assert event.target == "AAPL"
    assert event.timestamp is not None
