"""Tests for the concrete application run-loop owner."""

from power_core.runtime import Runtime
from power_framework.application import ApplicationBase, AsyncApplicationBase


class _TestApplication(AsyncApplicationBase):
    """An application that records its own start/stop."""

    def __init__(self, log: list[str]) -> None:
        self._log = log

    async def start(self) -> None:
        self._log.append("start:application")

    async def stop(self) -> None:
        self._log.append("stop:application")


def test_runtime_exposes_attached_application():
    runtime = Runtime()
    app = _TestApplication([])
    runtime.attach(app)
    assert runtime.application is app


async def test_run_async_drives_full_lifecycle_in_order():
    log: list[str] = []

    class App(AsyncApplicationBase):
        def __init__(self, entries: list[str]) -> None:
            self._entries = entries

        async def start(self) -> None:
            self._entries.append("start:application")

        async def run(self) -> None:
            self._entries.append("run:application")

        async def stop(self) -> None:
            self._entries.append("stop:application")

    runtime = Runtime()
    runtime.attach(App(log))

    await runtime.run_async()

    assert log == ["start:application", "run:application", "stop:application"]


async def test_run_async_drives_synchronous_application_in_order():
    log: list[str] = []

    class App(ApplicationBase):
        def __init__(self, entries: list[str]) -> None:
            self._entries = entries

        def start(self) -> None:
            self._entries.append("start:application")

        def run(self) -> None:
            self._entries.append("run:application")

        def stop(self) -> None:
            self._entries.append("stop:application")

    runtime = Runtime()
    runtime.attach(App(log))

    await runtime.run_async()

    assert log == ["start:application", "run:application", "stop:application"]


async def test_start_and_stop_accept_synchronous_application():
    log: list[str] = []

    class App(ApplicationBase):
        def __init__(self, entries: list[str]) -> None:
            self._entries = entries

        def start(self) -> None:
            self._entries.append("start:application")

        def stop(self) -> None:
            self._entries.append("stop:application")

    runtime = Runtime()
    runtime.attach(App(log))

    await runtime.start()
    await runtime.stop()

    assert log == ["start:application", "stop:application"]


def test_run_is_synchronous_and_owns_the_event_loop(monkeypatch):
    calls: list[str] = []

    class App(AsyncApplicationBase):
        async def run(self) -> None:
            calls.append("run")

    runtime = Runtime()
    runtime.attach(App())

    async def fake_run_async() -> None:
        calls.append("run_async")

    monkeypatch.setattr(runtime, "run_async", fake_run_async)

    # ``run()`` is synchronous: it returns None and drives ``run_async`` to
    # completion via ``asyncio.run`` before returning.
    runtime.run()

    assert calls == ["run_async"]


def test_run_drives_synchronous_application_without_an_event_loop(monkeypatch):
    log: list[str] = []

    class App(ApplicationBase):
        def __init__(self, entries: list[str]) -> None:
            self._entries = entries

        def start(self) -> None:
            self._entries.append("start:application")

        def run(self) -> None:
            self._entries.append("run:application")

        def stop(self) -> None:
            self._entries.append("stop:application")

    runtime = Runtime()
    runtime.attach(App(log))

    def fail_if_called() -> None:  # pragma: no cover - only raised if the wrong path runs
        raise AssertionError("run_async should not be called for a sync application")

    monkeypatch.setattr(runtime, "run_async", fail_if_called)

    # A fully synchronous application is driven directly, without ``asyncio``.
    runtime.run()

    assert log == ["start:application", "run:application", "stop:application"]
