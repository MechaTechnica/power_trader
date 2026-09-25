"""Tests for the framework health/readiness contracts."""

from power_framework.health import HealthReport, HealthStatus, Status


def test_health_status_healthy_and_unhealthy_helpers():
    healthy = HealthStatus.healthy("db", "ok")
    assert healthy.name == "db"
    assert healthy.status is Status.HEALTHY
    assert healthy.message == "ok"

    unhealthy = HealthStatus.unhealthy("db", "down", retries=1)
    assert unhealthy.status is Status.UNHEALTHY
    assert unhealthy.details == {"retries": 1}


def test_health_report_as_dict_is_serialisable():
    report = HealthReport(
        status=Status.UNHEALTHY,
        checks=[HealthStatus.unhealthy("db", "down", retries=1)],
    )
    data = report.as_dict()
    assert data["status"] == "unhealthy"
    assert data["checks"][0]["name"] == "db"
    assert data["checks"][0]["details"] == {"retries": 1}


def test_health_report_is_healthy_flag():
    healthy = HealthReport(status=Status.HEALTHY, checks=[])
    unhealthy = HealthReport(status=Status.UNHEALTHY, checks=[])

    assert healthy.is_healthy
    assert not unhealthy.is_healthy
