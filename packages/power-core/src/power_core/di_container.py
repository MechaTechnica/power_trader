"""Dependency injection container implementation."""

import importlib.metadata
from collections.abc import Callable
from typing import Any

from that_depends import BaseContainer

from power_core.exceptions import PluginError
from power_trader_framework.plugins import Plugin
from power_trader_framework.protocols.container import Container
from power_trader_framework.protocols.strategy import Strategy


class DIContainer(BaseContainer):
    """
    Dependency injection container for the application.

    Uses that-depends for automatic constructor injection based on type hints.
    Application-specific container extends this to register dependencies.
    """

    pass  # Extended in main.py with actual providers


class PluginRegistry:
    """
    Registry for strategy plugins.

    Discovers and loads strategy plugins from installed packages using entry
    points. Each plugin is a ``Plugin`` class whose ``register(container)``
    binds the strategy and its dependencies into the container it is given.
    """

    ENTRY_POINT_GROUP = "power_trader.strategies"

    def __init__(
        self,
        *,
        entry_point_group: str = ENTRY_POINT_GROUP,
        entry_points: Callable[..., Any] = importlib.metadata.entry_points,
    ) -> None:
        """Create a registry.

        Args:
            entry_point_group: Entry-point group to inspect. Supplying a custom
                group enables isolated application-specific plugin ecosystems.
            entry_points: Entry-point provider, injectable for deterministic
                tests and alternative package environments.
        """
        self._entry_point_group = entry_point_group
        self._entry_points = entry_points
        self._plugins: dict[str, type[Plugin]] = {}
        self._instances: dict[str, Strategy] = {}
        self._discovered: set[str] = set()

    def discover(self) -> tuple[str, ...]:
        """
        Discover strategy plugins using entry points.

        Each strategy registers itself via pyproject.toml:
        [project.entry-points."power_trader.strategies"]
        my_strategy = "my_package.plugin:MyPlugin"

        Raises:
            PluginError: If plugin loading fails
        """
        entry_points = self._entry_points()
        group = entry_points.select(group=self._entry_point_group)

        discovered: list[tuple[str, type[Plugin]]] = []
        discovered_names: set[str] = set()
        for entry_point in sorted(group, key=lambda candidate: candidate.name):
            if entry_point.name in self._discovered:
                continue
            try:
                plugin = entry_point.load()
                self._validate_plugin(entry_point.name, plugin)
                if entry_point.name in self._plugins or entry_point.name in discovered_names:
                    raise PluginError(f"Strategy '{entry_point.name}' already registered")
                discovered.append((entry_point.name, plugin))
                discovered_names.add(entry_point.name)
            except Exception as e:
                raise PluginError(
                    f"Failed to load strategy plugin '{entry_point.name}': {e}"
                ) from e

        # Register only after every entry point has loaded and validated, so a
        # failed discovery never leaves a partially populated registry.
        for name, plugin in discovered:
            self._plugins[name] = plugin
            self._discovered.add(name)
        return tuple(name for name, _ in discovered)

    def register(self, name: str, plugin_class: type[Plugin]) -> None:
        """Register a strategy plugin class under ``name``."""
        if name in self._plugins:
            raise PluginError(f"Strategy '{name}' already registered")
        self._validate_plugin(name, plugin_class)
        self._plugins[name] = plugin_class

    def build(self, container: Container) -> None:
        """Instantiate each strategy via its own child container.

        For each plugin, a child container is created, the plugin class is
        instantiated, its ``register()`` is called so it registers its services
        (and itself under ``Strategy``), and the strategy is then resolved from
        that container with constructor injection.
        """
        pending: dict[str, Strategy] = {}
        for name, plugin_class in self._plugins.items():
            if name in self._instances:
                continue
            child = container.create_child()
            try:
                plugin_class().register(child)
                pending[name] = child.resolve(Strategy)
            except Exception as e:
                raise PluginError(f"Failed to build strategy plugin '{name}': {e}") from e
        self._instances.update(pending)

    def get(self, name: str) -> Strategy:
        """Get a built strategy instance by name (singleton per strategy)."""
        if name not in self._plugins:
            raise PluginError(f"Strategy '{name}' not found")
        if name not in self._instances:
            raise PluginError(f"Strategy '{name}' has not been built; call build() first")
        return self._instances[name]

    def get_all(self) -> tuple[Strategy, ...]:
        """Get all built strategy instances."""
        return tuple(self._instances.values())

    def names(self) -> tuple[str, ...]:
        """Get names of all registered strategy plugins."""
        return tuple(self._plugins)

    async def initialize(self) -> None:
        """Initialize all built strategies."""
        for strategy in self.get_all():
            if hasattr(strategy, "initialize"):
                await strategy.initialize()

    async def cleanup(self) -> None:
        """Clean up all built strategies."""
        for strategy in self._instances.values():
            if hasattr(strategy, "cleanup"):
                await strategy.cleanup()

    @staticmethod
    def _validate_plugin(name: str, plugin: object) -> None:
        """Validate a loaded entry-point target before registering it."""
        if not isinstance(plugin, type) or not issubclass(plugin, Plugin):
            raise PluginError(f"Strategy '{name}' must expose a Plugin subclass, got {plugin!r}")
        if plugin.name is not None and plugin.name != name:
            raise PluginError(
                f"Strategy entry point '{name}' does not match plugin name '{plugin.name}'"
            )
