"""Tests for shared entry-point based application composition."""

from dataclasses import dataclass

from power_trader_framework.application import (CORE_NAME, PLUGIN_GROUP,
                                                _load_core,
                                                _load_plugin_factories)
from power_trader_framework.plugins import Plugin


class FirstApplicationPlugin(Plugin):
    """Application plugin used to verify entry-point ordering."""

    def register(self, container: object) -> None:
        """No wiring is required for entry-point selection tests."""


class SecondApplicationPlugin(Plugin):
    """A second application plugin used to verify entry-point ordering."""

    def register(self, container: object) -> None:
        """No wiring is required for entry-point selection tests."""


@dataclass(frozen=True)
class FakeEntryPoint:
    """Minimal importlib.metadata entry-point double."""

    name: str
    target: object

    def load(self) -> object:
        return self.target


class FakeEntryPoints:
    """Entry-point collection which records selector arguments."""

    def __init__(self, entries: list[FakeEntryPoint]) -> None:
        self.entries = entries
        self.calls: list[tuple[str, str | None]] = []

    def select(self, *, group: str, name: str | None = None) -> list[FakeEntryPoint]:
        self.calls.append((group, name))
        return [entry for entry in self.entries if name is None or entry.name == name]


def test_runtime_is_loaded_from_core_in_the_shared_group(monkeypatch):
    def runtime_factory(*_args: object) -> object:
        return object()

    entries = FakeEntryPoints([FakeEntryPoint(CORE_NAME, runtime_factory)])
    monkeypatch.setattr("importlib.metadata.entry_points", lambda: entries)

    assert _load_core() is runtime_factory
    assert entries.calls == [(PLUGIN_GROUP, CORE_NAME)]


def test_load_plugin_factories_excludes_core_and_loads_all_plugins(monkeypatch):
    entries = FakeEntryPoints(
        [
            FakeEntryPoint("strategy.momentum", SecondApplicationPlugin),
            FakeEntryPoint("application.second", SecondApplicationPlugin),
            FakeEntryPoint(CORE_NAME, object()),
            FakeEntryPoint("application.first", FirstApplicationPlugin),
        ]
    )
    monkeypatch.setattr("importlib.metadata.entry_points", lambda: entries)

    plugins = _load_plugin_factories()

    # Sorted by entry-point name; ``core`` excluded.
    assert plugins == [
        FirstApplicationPlugin,
        SecondApplicationPlugin,
        SecondApplicationPlugin,
    ]
    assert entries.calls == [(PLUGIN_GROUP, None)]

