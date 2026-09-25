"""Tests for the runtime-owned lifecycle manager."""

import pytest

from power_framework.application import ApplicationBase, Runtime
from power_framework.exceptions import LifecycleError


class _RecordingComponent:
    """A lifecycle component that records when it is started/stopped."""

    def __init__(self, name: str, log: list[str]) -> None:
        self._name = name
        self._log = log

    async def start(self) -> None:
        self._log.append(f"start:{self._name}")

    async def stop(self) -> None:
        self._log.append(f"stop:{self._name}")


class _FakeContainer:
    """A container double that resolves registered component types by key."""

    def __init__(self, components: dict[type, object]) -> None:
        self._components = components

    def resolve(self, interface: type) -> object:
        return self._components[interface]


class _TestApplication(ApplicationBase):
    """An application that records its own start/stop."""

    def __init__(self, log: list[str]) -> None:
        self._log = log

    async def start(self) -> None:
        self._log.append("start:application")

    async def stop(self) -> None:
        self._log.append("stop:application")


class _Infrastructure:
    """Marker type for the infrastructure lifecycle component."""


class _Domain:
    """Marker type for the domain-services lifecycle component."""


async def test_runtime_starts_in_order_and_stops_in_reverse():
    log: list[str] = []
    container = _FakeContainer(
        {
            _Infrastructure: _RecordingComponent("infrastructure", log),
            _Domain: _RecordingComponent("domain", log),
        }
    )

    runtime = Runtime(container)  # type: ignore[arg-type]
    runtime.register(_Infrastructure)
    runtime.register(_Domain)
    runtime.attach(_TestApplication(log))

    await runtime.start()
    assert log == ["start:infrastructure", "start:domain", "start:application"]

    await runtime.stop()
    assert log == [
        "start:infrastructure",
        "start:domain",
        "start:application",
        "stop:application",
        "stop:domain",
        "stop:infrastructure",
    ]


def test_runtime_exposes_attached_application():
    runtime = Runtime(_FakeContainer({}))  # type: ignore[arg-type]
    app = _TestApplication([])
    runtime.attach(app)
    assert runtime.application is app


async def test_shutdown_attempts_all_components_despite_failures():
    log: list[str] = []

    class FailingComponent:
        async def stop(self) -> None:
            log.append("stop:failing")
            raise RuntimeError("boom")

    class HealthyComponent:
        async def stop(self) -> None:
            log.append("stop:healthy")

    container = _FakeContainer(
        {
            _Infrastructure: FailingComponent(),
            _Domain: HealthyComponent(),
        }
    )
    runtime = Runtime(container)  # type: ignore[arg-type]
    runtime.register(_Infrastructure)
    runtime.register(_Domain)
    runtime.attach(_TestApplication(log))

    with pytest.raises(LifecycleError):
        await runtime.stop()

    # Both components were given a chance to stop, despite the first failing.
    assert "stop:failing" in log
    assert "stop:healthy" in log


async def test_run_async_drives_full_lifecycle_in_order():
    log: list[str] = []

    class App(ApplicationBase):
        def __init__(self, entries: list[str]) -> None:
            self._entries = entries

        async def start(self) -> None:
            self._entries.append("start:application")

        async def run(self) -> None:
            self._entries.append("run:application")

        async def stop(self) -> None:
            self._entries.append("stop:application")

    runtime = Runtime(_FakeContainer({}))  # type: ignore[arg-type]
    runtime.attach(App(log))

    await runtime.run_async()

    assert log == ["start:application", "run:application", "stop:application"]


def test_run_is_synchronous_and_owns_the_event_loop(monkeypatch):
    calls: list[str] = []

    class App(ApplicationBase):
        async def run(self) -> None:
            calls.append("run")

    runtime = Runtime(_FakeContainer({}))  # type: ignore[arg-type]
    runtime.attach(App())

    async def fake_run_async() -> None:
        calls.append("run_async")

    monkeypatch.setattr(runtime, "run_async", fake_run_async)

    # ``run()`` is synchronous: it returns None and drives ``run_async`` to
    # completion via ``asyncio.run`` before returning.
    runtime.run()

    assert calls == ["run_async"]
