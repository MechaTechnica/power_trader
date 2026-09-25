"""Framework error model.

Three types cover the framework's needs:

- :class:`FrameworkError` — a failure of the framework machinery (configuration,
  dependency resolution, plugin loading, lifecycle). Not retryable.
- :class:`InfrastructureError` — a transient failure of a framework-managed
  service; carries ``retryable = True`` so the retry interceptor reacts.
- :class:`ApplicationError` — a business failure raised by domain code, handled
  at the application level rather than by the runtime.

Rule of thumb: raise :class:`FrameworkError` for anything the framework itself
gets wrong, :class:`InfrastructureError` for transient external-service
failures, and :class:`ApplicationError` for domain/business failures. Distinguish
specific causes by the message, not by adding more subclasses.
"""

from typing import ClassVar


class FrameworkError(Exception):
    """Base for failures of the framework machinery."""

    #: Whether this category of error is transient and safe to retry.
    retryable: ClassVar[bool] = False


class InfrastructureError(FrameworkError):
    """A framework-managed service failed transiently (retry)."""

    retryable = True


class ApplicationError(Exception):
    """Base for errors raised by application/domain code (not framework errors)."""


def is_retryable(error: BaseException) -> bool:
    """Return ``True`` if ``error`` is classified as transient and retryable."""
    return bool(getattr(type(error), "retryable", False))


__all__ = [
    "ApplicationError",
    "FrameworkError",
    "InfrastructureError",
    "is_retryable",
]
