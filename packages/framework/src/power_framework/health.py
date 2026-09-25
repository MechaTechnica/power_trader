"""Framework health/readiness contracts.

Production applications expose two platform conventions:

- **Liveness** (``/health``): "is the process running and able to respond?"
- **Readiness** (``/ready``): "can this process serve traffic right now?"

Readiness is expressed as a set of named :class:`HealthCheck` components (IB
connection, market data, strategies loaded, database, messaging, ...) that each
report a :class:`HealthStatus`. The framework aggregates them into a single
:class:`HealthReport`.

This module owns the *contracts* only: the value types (:class:`Status`,
:class:`HealthStatus`, :class:`HealthReport`) and the protocols
(:class:`HealthCheck`, :class:`HealthCheckRegistry`, :class:`HealthService`).
The concrete registry and service live in ``power_core.health``.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, Self


class Status(StrEnum):
    """Overall health of a component or the whole service."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True)
class HealthStatus:
    """The result of a single :class:`HealthCheck`."""

    name: str
    status: Status
    message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def healthy(cls, name: str, message: str | None = None) -> Self:
        return cls(name=name, status=Status.HEALTHY, message=message)

    @classmethod
    def unhealthy(cls, name: str, message: str | None = None, **details: Any) -> Self:
        return cls(name=name, status=Status.UNHEALTHY, message=message, details=details)


class HealthCheck(Protocol):
    """A named readiness probe."""

    name: str

    async def check(self) -> HealthStatus:
        """Return this component's current health."""
        ...


class HealthCheckRegistry(Protocol):
    """Collects :class:`HealthCheck` components and runs them on demand (contract)."""

    def register(self, check: HealthCheck) -> None:
        """Register a readiness check, in the order it should be evaluated."""
        ...

    @property
    def checks(self) -> list[HealthCheck]:
        """The registered checks, in evaluation order."""
        ...

    async def run_all(self) -> list[HealthStatus]:
        """Run every registered check and return one status per check."""
        ...


@dataclass(frozen=True)
class HealthReport:
    """Aggregate health across all checks."""

    status: Status
    checks: list[HealthStatus]

    @property
    def is_healthy(self) -> bool:
        return self.status is Status.HEALTHY

    def as_dict(self) -> dict[str, Any]:
        """Serialisable view suitable for ``/health`` / ``/ready`` responses."""
        return {
            "status": self.status.value,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "details": c.details,
                }
                for c in self.checks
            ],
        }


class HealthService(Protocol):
    """Coordinates liveness and readiness reporting for a service (contract)."""

    async def liveness(self) -> HealthReport:
        """Report liveness (the process can respond), independent of dependencies."""
        ...

    async def readiness(self) -> HealthReport:
        """Report readiness by running all registered dependency checks."""
        ...


__all__ = [
    "HealthCheck",
    "HealthCheckRegistry",
    "HealthReport",
    "HealthService",
    "HealthStatus",
    "Status",
]
