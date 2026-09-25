"""Tests for the framework error model."""

from power_framework.exceptions import (
    ApplicationError,
    FrameworkError,
    InfrastructureError,
    is_retryable,
)


def test_infrastructure_error_is_a_framework_error():
    assert issubclass(InfrastructureError, FrameworkError)


def test_application_errors_are_separate_from_framework_errors():
    assert not issubclass(ApplicationError, FrameworkError)
    assert not issubclass(FrameworkError, ApplicationError)


def test_infrastructure_error_is_retryable_by_default():
    assert InfrastructureError.retryable is True
    assert FrameworkError.retryable is False


def test_is_retryable_uses_the_category_flag():
    assert is_retryable(InfrastructureError("transient"))
    assert not is_retryable(FrameworkError("bad config"))
    assert not is_retryable(ApplicationError("invalid order"))
    assert not is_retryable(ValueError("plain error"))
