"""Tests for the framework error model."""

from power_framework.exceptions import (
    ApplicationError,
    ConfigurationError,
    DependencyError,
    DomainError,
    FrameworkError,
    InfrastructureError,
    LifecycleError,
    PluginError,
    is_retryable,
)


def test_framework_errors_form_a_hierarchy():
    assert issubclass(ConfigurationError, FrameworkError)
    assert issubclass(DependencyError, FrameworkError)
    assert issubclass(LifecycleError, FrameworkError)
    assert issubclass(PluginError, FrameworkError)
    assert issubclass(InfrastructureError, FrameworkError)


def test_application_errors_are_separate_from_framework_errors():
    assert issubclass(DomainError, ApplicationError)
    assert not issubclass(ApplicationError, FrameworkError)
    assert not issubclass(DomainError, FrameworkError)


def test_infrastructure_error_is_retryable_by_default():
    assert InfrastructureError.retryable is True
    assert ConfigurationError.retryable is False
    assert DependencyError.retryable is False


def test_is_retryable_uses_the_category_flag():
    assert is_retryable(InfrastructureError("transient"))
    assert not is_retryable(ConfigurationError("bad config"))
    assert not is_retryable(DomainError("invalid order"))
    assert not is_retryable(ValueError("plain error"))
