"""Tests for the framework health/readiness capability."""

import pytest

from power_framework.health import (
    HealthCheckRegistry,
    HealthReport,
    HealthService,
    HealthStatus,
    Status,
)


class _HealthyCheck:
    name = "healthy_component"

    async def check(self) -> HealthStatus:
        return HealthStatus.healthy(self.name, "all good")


class _UnhealthyCheck:
    name = "broken_component"

    async def check(self) -> HealthStatus:
        return HealthStatus.unhealthy(self.name, "connection refused", retries=3)


class _RaisingCheck:
    name = "crashing_component"

    async def check(self) -> HealthStatus:
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_registry_runs_all_checks():
    registry = HealthCheckRegistry()
    registry.register(_HealthyCheck())
    registry.register(_UnhealthyCheck())

    results = await registry.run_all()
    assert [r.name for r in results] == ["healthy_component", "broken_component"]
    assert results[0].status is Status.HEALTHY
    assert results[1].status is Status.UNHEALTHY


@pytest.mark.asyncio
async def test_failing_check_is_captured_as_unhealthy():
    registry = HealthCheckRegistry()
    registry.register(_RaisingCheck())

    results = await registry.run_all()
    assert results[0].status is Status.UNHEALTHY
    assert "boom" in (results[0].message or "")


@pytest.mark.asyncio
async def test_readiness_aggregates_to_unhealthy_when_any_check_fails():
    registry = HealthCheckRegistry()
    registry.register(_HealthyCheck())
    registry.register(_UnhealthyCheck())

    service = HealthService(registry)
    report = await service.readiness()

    assert report.status is Status.UNHEALTHY
    assert not report.is_healthy


@pytest.mark.asyncio
async def test_readiness_healthy_when_all_checks_pass():
    registry = HealthCheckRegistry()
    registry.register(_HealthyCheck())

    report = await HealthService(registry).readiness()
    assert report.status is Status.HEALTHY


@pytest.mark.asyncio
async def test_liveness_is_always_healthy():
    report = await HealthService(HealthCheckRegistry()).liveness()
    assert report.status is Status.HEALTHY
    assert report.checks == []


def test_health_report_as_dict_is_serialisable():
    report = HealthReport(
        status=Status.UNHEALTHY,
        checks=[HealthStatus.unhealthy("db", "down", retries=1)],
    )
    data = report.as_dict()
    assert data["status"] == "unhealthy"
    assert data["checks"][0]["name"] == "db"
    assert data["checks"][0]["details"] == {"retries": 1}
