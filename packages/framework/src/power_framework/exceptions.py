"""Framework error model.

The framework owns the *error vocabulary* so the runtime can produce consistent
behaviour regardless of which application runs on top of it. Two families are
distinguished:

**Framework errors** (:class:`FrameworkError`) — failures of the framework
machinery itself. The runtime maps each to a consistent behaviour:

- :class:`ConfigurationError` → *fail fast* (invalid or missing configuration).
- :class:`DependencyError` → *fail startup* (a dependency cannot be built).
- :class:`LifecycleError` → *fail startup/shutdown*.
- :class:`PluginError` → *fail startup* (a plugin cannot be loaded/registered).
- :class:`InfrastructureError` → *retry* (transient infrastructure failure).

**Application errors** (:class:`ApplicationError`) — failures raised by
application/domain code. These are handled at the application level, not by the
runtime, because they represent business outcomes rather than framework failures:

- :class:`DomainError` → *application-level handling* (domain rule/validation).
"""

from __future__ import annotations

from typing import ClassVar


class FrameworkError(Exception):
    """Base class for failures of the framework machinery itself.

    Each subclass carries a :attr:`retryable` flag describing whether the failure
    is transient and therefore safe to retry, so the runtime and interceptors can
    react consistently without inspecting message strings.
    """

    #: Whether this category of error is transient and safe to retry.
    retryable: ClassVar[bool] = False


class ConfigurationError(FrameworkError):
    """Configuration is invalid or missing.

    Mapped by the runtime to *fail fast*: the process aborts before doing any
    work rather than running with a broken configuration.
    """


class DependencyError(FrameworkError):
    """A required dependency could not be resolved or constructed.

    Mapped by the runtime to *fail startup*: the dependency graph is incomplete,
    so the application cannot begin serving.
    """


class DependencyValidationError(DependencyError):
    """The application's dependency graph is incomplete.

    Raised by :meth:`Container.validate` (or the builder's ``validate`` phase)
    before the application is constructed. The message is a human-readable
    dependency tree in which each dependency is annotated with ``✓`` (resolvable)
    or ``✗ missing`` (no registration), so wiring mistakes are surfaced
    deterministically at startup rather than at first resolve.
    """


class LifecycleError(FrameworkError):
    """A lifecycle component failed to start or stop.

    Mapped by the runtime to *fail startup/shutdown*: a component could not reach
    a usable state (or could not clean up), so the ordered lifecycle is aborted.
    """


class PluginError(FrameworkError):
    """A plugin failed to load or register.

    Mapped by the runtime to *fail startup*: an extension point exposed something
    invalid, so composition cannot proceed.
    """


class InfrastructureError(FrameworkError):
    """A framework-managed infrastructure service failed transiently.

    Mapped by the runtime to *retry*: the failure is expected to be transient
    (network, broker connection, message bus), so callers may back off and retry.
    """

    retryable = True


class ApplicationError(Exception):
    """Base class for errors raised by application/domain code.

    These do not subclass :class:`FrameworkError`: they represent business
    failures (invalid input, violated invariants, rejected operations) that the
    application itself must interpret and respond to.
    """


class DomainError(ApplicationError):
    """A domain rule or validation invariant was violated.

    This is the application-level "reject this operation" signal. Handlers
    translate it into an appropriate response (e.g. a 4xx, a rejected order)
    rather than letting it crash the process.
    """


def is_retryable(error: BaseException) -> bool:
    """Return ``True`` if ``error`` is classified as transient and retryable.

    Retryability is a property of the error *category* (declared via the
    :attr:`FrameworkError.retryable` class attribute) rather than a message match,
    so retry interceptors and the runtime share one source of truth.
    """
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
