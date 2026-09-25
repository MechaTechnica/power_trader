"""Tests for the concrete observability implementations (structured/terminal loggers, redact)."""

import json
import logging
from io import StringIO

from power_core.observability import StructuredLogger, TerminalLogger, redact
from power_framework.observability import Redacted, Secret, correlation_scope


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
