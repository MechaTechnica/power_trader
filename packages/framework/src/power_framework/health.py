"""Framework health/readiness capability.

Production applications expose two platform conventions:

- **Liveness** (``/health``): "is the process running and able to respond?"
- **Readiness** (``/ready``): "can this process serve traffic right now?"

Readiness is expressed as a set of named :class:`HealthCheck` components (IB
connection, market data, strategies loaded, database, messaging, ...) that each
report a :class:`HealthStatus`. The framework aggregates them into a single
:class:`HealthReport` so applications never hand-roll their own health stack.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class Status(str, Enum):
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
    def healthy(cls, name: str, message: str | None = None) -> HealthStatus:
        return cls(name=name, status=Status.HEALTHY, message=message)

    @classmethod
    def unhealthy(
        cls, name: str, message: str | None = None, **details: Any
    ) -> HealthStatus:
        return cls(name=name, status=Status.UNHEALTHY, message=message, details=details)


class HealthCheck(Protocol):
    """A named readiness probe."""

    name: str

    async def check(self) -> HealthStatus:
        """Return this component's current health."""
        ...


class HealthCheckRegistry:
    """Collects :class:`HealthCheck` components and runs them on demand."""

    def __init__(self) -> None:
        self._checks: list[HealthCheck] = []

    def register(self, check: HealthCheck) -> None:
        """Register a readiness check, in the order it should be evaluated."""
        self._checks.append(check)

    @property
    def checks(self) -> list[HealthCheck]:
        return list(self._checks)

    async def run_all(self) -> list[HealthStatus]:
        """Run every registered check, capturing failures rather than raising."""
        results: list[HealthStatus] = []
        for check in self._checks:
            try:
                results.append(await check.check())
            except Exception as exc:
                results.append(
                    HealthStatus.unhealthy(check.name, str(exc))
                )
        return results


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


def _overall_status(statuses: list[Status]) -> Status:
    if Status.UNHEALTHY in statuses:
        return Status.UNHEALTHY
    if Status.DEGRADED in statuses:
        return Status.DEGRADED
    return Status.HEALTHY


class HealthService:
    """Coordinates liveness and readiness reporting for a service."""

    def __init__(self, registry: HealthCheckRegistry) -> None:
        self._registry = registry

    async def liveness(self) -> HealthReport:
        """Report liveness (the process can respond), independent of dependencies."""
        return HealthReport(status=Status.HEALTHY, checks=[])

    async def readiness(self) -> HealthReport:
        """Report readiness by running all registered dependency checks."""
        checks = await self._registry.run_all()
        status = _overall_status([c.status for c in checks])
        return HealthReport(status=status, checks=checks)


__all__ = [
    "HealthCheck",
    "HealthCheckRegistry",
    "HealthReport",
    "HealthService",
    "HealthStatus",
    "Status",
]
