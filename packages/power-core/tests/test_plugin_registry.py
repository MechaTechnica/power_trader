"""Tests for deterministic, entry-point based strategy plugin discovery."""

from dataclasses import dataclass
from typing import Any

import pytest
from power_core.di_container import PluginRegistry
from power_core.exceptions import PluginError

from power_trader_framework.plugins import Plugin


class ExamplePlugin(Plugin):
    """A valid plugin used to exercise registry discovery."""

    name = "example"

    def register(self, container: Any) -> None:
        """The discovery tests do not need container wiring."""


class OtherPlugin(Plugin):
    """A second valid plugin used to verify stable ordering."""

    name = "other"

    def register(self, container: Any) -> None:
        """The discovery tests do not need container wiring."""


@dataclass(frozen=True)
class FakeEntryPoint:
    """Minimal entry-point double compatible with the registry."""

    name: str
    target: object

    def load(self) -> object:
        """Return the configured entry-point target."""
        return self.target


class FakeEntryPoints:
    """Minimal entry-point collection double."""

    def __init__(self, entries: list[FakeEntryPoint]) -> None:
        self._entries = entries
        self.groups: list[str] = []

    def select(self, *, group: str) -> list[FakeEntryPoint]:
        """Record the selected group and return configured entries."""
        self.groups.append(group)
        return self._entries


def registry_for(entries: list[FakeEntryPoint]) -> tuple[PluginRegistry, FakeEntryPoints]:
    """Create a registry with a deterministic installed-package view."""
    entry_points = FakeEntryPoints(entries)

    def provider() -> FakeEntryPoints:
        return entry_points

    return PluginRegistry(entry_points=provider), entry_points


def test_discover_registers_plugins_in_stable_name_order():
    registry, entry_points = registry_for(
        [FakeEntryPoint("other", OtherPlugin), FakeEntryPoint("example", ExamplePlugin)]
    )

    assert registry.discover() == ("example", "other")
    assert registry.names() == ("example", "other")
    assert entry_points.groups == ["power_trader.strategies"]


def test_discover_is_idempotent():
    registry, _ = registry_for([FakeEntryPoint("example", ExamplePlugin)])

    assert registry.discover() == ("example",)
    assert registry.discover() == ()
    assert registry.names() == ("example",)


def test_discover_rejects_a_plugin_with_a_mismatched_declared_name():
    registry, _ = registry_for([FakeEntryPoint("incorrect", ExamplePlugin)])

    with pytest.raises(PluginError, match="does not match plugin name"):
        registry.discover()

    assert registry.names() == ()


def test_discover_is_atomic_when_one_entry_point_is_invalid():
    registry, _ = registry_for(
        [FakeEntryPoint("example", ExamplePlugin), FakeEntryPoint("bad", object)]
    )

    with pytest.raises(PluginError, match="must expose a Plugin subclass"):
        registry.discover()

    assert registry.names() == ()
