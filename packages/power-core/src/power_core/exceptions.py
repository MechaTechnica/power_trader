"""Runtime exceptions, aligned to the framework error model.

``power-core`` builds concrete failures on top of the framework's taxonomy so
applications can catch the framework types (``DependencyError``,
``InfrastructureError``, ...) without importing runtime internals.
"""

from power_framework.exceptions import (
    ApplicationError,
    ConfigurationError,
    DependencyError,
    DependencyValidationError,
    DomainError,
    FrameworkError,
    InfrastructureError,
    LifecycleError,
    PluginError,
)


class DIError(DependencyError):
    """Dependency-injection resolution or construction failed."""


class ConnectionError(InfrastructureError):
    """Connection to an external service failed (transient/retryable)."""


class StrategyError(ApplicationError):
    """A strategy raised an error during execution."""


__all__ = [
    "ApplicationError",
    "ConfigurationError",
    "ConnectionError",
    "DIError",
    "DependencyError",
    "DependencyValidationError",
    "DomainError",
    "FrameworkError",
    "InfrastructureError",
    "LifecycleError",
    "PluginError",
    "StrategyError",
]
