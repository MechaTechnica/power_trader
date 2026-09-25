"""Tests for shared entry-point based application composition."""

from dataclasses import dataclass

from pydantic_settings import SettingsConfigDict

from power_framework.application import CORE_GROUP, PLUGIN_GROUP, ApplicationBootstrapper
from power_framework.plugins import Plugin
from power_framework.settings import Settings


class FirstApplicationPlugin(Plugin):
    """Application plugin used to verify entry-point ordering."""

    def register(self, container: object, runtime: object) -> None:
        """No wiring is required for entry-point selection tests."""


class SecondApplicationPlugin(Plugin):
    """A second application plugin used to verify entry-point ordering."""

    def register(self, container: object, runtime: object) -> None:
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


def test_register_plugin_settings_loads_and_registers_settings():
    class AppSettings(Settings):
        model_config = SettingsConfigDict(env_prefix="TEST_APP_")

        foo: str = "bar"

    class ConfigPlugin(Plugin):
        settings_class = AppSettings

        def register(self, container: object, runtime: object) -> None:
            """No wiring required for this test."""

    registered: dict[type, object] = {}

    class FakeContainer:
        def register_instance(self, interface: type, instance: object) -> None:
            registered[interface] = instance

    ApplicationBootstrapper._register_plugin_settings(FakeContainer(), ConfigPlugin())

    assert AppSettings in registered
    assert registered[AppSettings].foo == "bar"  # type: ignore[union-attr]


def test_register_plugin_settings_is_noop_without_settings_class():
    class NoSettingsPlugin(Plugin):
        def register(self, container: object, runtime: object) -> None:
            """No wiring required for this test."""

    registered: dict[type, object] = {}

    class FakeContainer:
        def register_instance(self, interface: type, instance: object) -> None:
            registered[interface] = instance

    ApplicationBootstrapper._register_plugin_settings(FakeContainer(), NoSettingsPlugin())

    assert registered == {}


def test_runtime_is_loaded_from_core_in_its_own_group(monkeypatch):
    def runtime_factory(*_args: object) -> object:
        return object()

    entries = FakeEntryPoints([FakeEntryPoint("power-core", runtime_factory)])
    monkeypatch.setattr("power_framework.application._get_entry_points", lambda: entries)

    bootstrapper = ApplicationBootstrapper()
    assert bootstrapper._load_core_entry_point() is runtime_factory
    assert entries.calls == [(CORE_GROUP, None)]


def test_load_plugin_factories_loads_all_plugins(monkeypatch):
    entries = FakeEntryPoints(
        [
            FakeEntryPoint("strategy.momentum", SecondApplicationPlugin),
            FakeEntryPoint("application.second", SecondApplicationPlugin),
            FakeEntryPoint("application.first", FirstApplicationPlugin),
        ]
    )
    monkeypatch.setattr("power_framework.application._get_entry_points", lambda: entries)

    bootstrapper = ApplicationBootstrapper()
    plugins = bootstrapper._load_plugins()

    # ``SecondApplicationPlugin`` appears under two entry points but is
    # deduplicated by type.
    assert plugins == {FirstApplicationPlugin, SecondApplicationPlugin}
    assert entries.calls == [(PLUGIN_GROUP, None)]


def test_load_plugins_honours_allowlist(monkeypatch):
    entries = FakeEntryPoints(
        [
            FakeEntryPoint("application.first", FirstApplicationPlugin),
            FakeEntryPoint("application.second", SecondApplicationPlugin),
        ]
    )
    monkeypatch.setattr("power_framework.application._get_entry_points", lambda: entries)

    bootstrapper = ApplicationBootstrapper()
    # Only the entry-point name "application.first" is authorized.
    plugins = bootstrapper._load_plugins(allowlist={"application.first"})

    assert plugins == {FirstApplicationPlugin}
