"""Framework error model.

Two families:

- :class:`FrameworkError` — failures of the framework itself. Subclasses carry a
  :attr:`retryable` flag so the runtime and interceptors react consistently.
- :class:`ApplicationError` — business failures raised by domain code, handled at
  the application level rather than by the runtime.
"""

from __future__ import annotations

from typing import ClassVar


class FrameworkError(Exception):
    """Base for failures of the framework machinery."""

    #: Whether this category of error is transient and safe to retry.
    retryable: ClassVar[bool] = False


class ConfigurationError(FrameworkError):
    """Configuration is invalid or missing (fail fast)."""


class DependencyError(FrameworkError):
    """A required dependency could not be resolved (fail startup)."""


class DependencyValidationError(DependencyError):
    """The dependency graph is incomplete.

    Raised by ``Container.validate`` before construction, with a tree annotating
    each dependency as ``✓`` (resolvable) or ``✗ missing`` (unregistered).
    """


class LifecycleError(FrameworkError):
    """A lifecycle component failed to start or stop."""


class PluginError(FrameworkError):
    """A plugin failed to load or register (fail startup)."""


class InfrastructureError(FrameworkError):
    """A framework-managed service failed transiently (retry)."""

    retryable = True


class ApplicationError(Exception):
    """Base for errors raised by application/domain code (not framework errors)."""


class DomainError(ApplicationError):
    """A domain rule or validation invariant was violated."""


def is_retryable(error: BaseException) -> bool:
    """Return ``True`` if ``error`` is classified as transient and retryable."""
    return bool(getattr(type(error), "retryable", False))


__all__ = [
    "ApplicationError",
    "ConfigurationError",
    "DependencyError",
    "DependencyValidationError",
    "DomainError",
    "FrameworkError",
    "InfrastructureError",
    "LifecycleError",
    "PluginError",
    "is_retryable",
]
