"""Tests for the framework's test builder and test harness."""

from power_framework.application import ApplicationBase, ApplicationBootstrapper
from power_framework.events import Event, EventBus
from power_framework.observability import Metrics, Tracer
from power_framework.testing import ApplicationTestHarness
from power_framework.testing import TestApplicationBuilder as TestAppBuilder


class _TestApp(ApplicationBase):
    """An application type used by the builder/harness tests."""


class _FakeDatabase:
    """Placeholder for an application adapter swapped in tests."""


def test_test_application_builder_accumulates_and_passes_overrides(monkeypatch):
    captured: dict[str, object] = {}

    def fake_bootstrap(
        bootstrapper: object,
        app_class: object,
        *,
        validate: bool = False,
        overrides: object = None,
        framework_overrides: object = None,
    ) -> object:
        captured["bootstrapper"] = bootstrapper
        captured["app_class"] = app_class
        captured["validate"] = validate
        captured["overrides"] = overrides
        captured["framework_overrides"] = framework_overrides
        return object()

    monkeypatch.setattr(ApplicationBootstrapper, "bootstrap", fake_bootstrap)

    builder = TestAppBuilder(_TestApp).replace(_FakeDatabase, _FakeDatabase())
    builder.build()

    assert captured["app_class"] is _TestApp
    assert captured["validate"] is False
    assert captured["framework_overrides"] is None
    overrides = captured["overrides"]
    assert isinstance(overrides, list)
    assert len(overrides) == 1
    assert overrides[0][0] is _FakeDatabase


def test_test_application_builder_validate_passes_overrides(monkeypatch):
    captured: dict[str, object] = {}

    def fake_validate(
        bootstrapper: object,
        app_class: object,
        *,
        overrides: object = None,
        framework_overrides: object = None,
    ) -> None:
        captured["bootstrapper"] = bootstrapper
        captured["app_class"] = app_class
        captured["overrides"] = overrides
        captured["framework_overrides"] = framework_overrides

    monkeypatch.setattr(ApplicationBootstrapper, "validate", fake_validate)

    builder = TestAppBuilder(_TestApp).replace(_FakeDatabase, _FakeDatabase())
    builder.validate()

    assert captured["app_class"] is _TestApp
    assert captured["framework_overrides"] is None
    overrides = captured["overrides"]
    assert isinstance(overrides, list)
    assert len(overrides) == 1
    assert overrides[0][0] is _FakeDatabase


def test_harness_provides_framework_fakes(monkeypatch):
    captured: dict[str, object] = {}

    def fake_bootstrap(
        bootstrapper: object,
        app_class: object,
        *,
        validate: bool = False,
        overrides: object = None,
        framework_overrides: object = None,
    ) -> object:
        captured["bootstrapper"] = bootstrapper
        captured["app_class"] = app_class
        captured["validate"] = validate
        captured["framework_overrides"] = framework_overrides
        captured["overrides"] = overrides
        return object()

    monkeypatch.setattr(ApplicationBootstrapper, "bootstrap", fake_bootstrap)

    harness = ApplicationTestHarness(_TestApp).replace(_FakeDatabase, _FakeDatabase())
    harness.build()

    framework_overrides = captured["framework_overrides"]
    assert framework_overrides[EventBus] is harness.event_bus
    assert framework_overrides[Metrics] is harness.metrics
    assert framework_overrides[Tracer] is harness.tracer

    overrides = captured["overrides"]
    assert isinstance(overrides, list)
    assert len(overrides) == 1
    assert overrides[0][0] is _FakeDatabase


async def test_harness_records_published_events():
    harness = ApplicationTestHarness(_TestApp)

    event = Event()
    await harness.publish(event)

    assert harness.captured_events == [event]
    assert len(harness.captured_spans) == 0
