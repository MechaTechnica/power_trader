"""Framework health/readiness capability.

Production applications expose two platform conventions:

- **Liveness** (``/health``): "is the process running and able to respond?"
- **Readiness** (``/ready``): "can this process serve traffic right now?"

Readiness is expressed as a set of named :class:`HealthCheck` components (IB
connection, market data, strategies loaded, database, messaging, ...) that each
report a :class:`HealthStatus`. The framework aggregates them into a single
:class:`HealthReport` so applications never hand-roll their own health stack.
"""

import asyncio
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
        """Run every registered check concurrently, capturing failures.

        Checks run together via ``asyncio.gather`` so a slow dependency (e.g. a
        200 ms database probe) does not serialize behind other probes. Each
        check's failure is isolated into an ``unhealthy`` status rather than
        aborting the whole readiness evaluation.
        """
        results = await asyncio.gather(
            *(self._run_one(check) for check in self._checks),
            return_exceptions=True,
        )
        statuses: list[HealthStatus] = []
        for check, result in zip(self._checks, results, strict=True):
            if isinstance(result, BaseException):
                statuses.append(HealthStatus.unhealthy(check.name, str(result)))
            else:
                statuses.append(result)
        return statuses

    @staticmethod
    async def _run_one(check: HealthCheck) -> HealthStatus:
        try:
            return await check.check()
        except Exception as exc:
            return HealthStatus.unhealthy(check.name, str(exc))


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
