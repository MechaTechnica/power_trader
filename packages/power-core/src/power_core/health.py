"""Health/readiness implementations.

``power_framework.health`` declares the contracts (``HealthCheck``,
``HealthCheckRegistry``, ``HealthService`` and their value types). This module
provides the concrete registry and service that the runtime registers in the
container.
"""

import asyncio

from power_framework.health import (HealthCheck, HealthReport, HealthStatus,
                                    Status)


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
    "HealthCheckRegistry",
    "HealthService",
]