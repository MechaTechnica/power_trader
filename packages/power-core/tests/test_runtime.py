"""Tests for the concrete application run-loop owner."""

from power_core.runtime import Runtime
from power_framework.application import ApplicationBase


class _TestApplication(ApplicationBase):
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

    class App(ApplicationBase):
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


def test_run_is_synchronous_and_owns_the_event_loop(monkeypatch):
    calls: list[str] = []

    class App(ApplicationBase):
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