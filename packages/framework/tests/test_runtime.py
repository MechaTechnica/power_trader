"""Tests for the runtime-owned lifecycle manager."""

from power_framework.application import ApplicationBase, Runtime


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
