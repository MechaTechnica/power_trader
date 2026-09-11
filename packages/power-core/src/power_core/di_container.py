"""Dependency injection container implementation."""

import importlib.metadata
from typing import Any

from power_core.exceptions import PluginError
from power_trader_framework.plugins import Plugin
from power_trader_framework.protocols.container import Container
from power_trader_framework.protocols.strategy import Strategy
from that_depends import BaseContainer


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
    points. Each plugin is a ``register(container)`` function (in its package's
    ``plugin.py``) that registers the strategy and its dependencies into the
    container it is given.
    """

    ENTRY_POINT_GROUP = "power_trader.strategies"

    def __init__(self) -> None:
        self._plugins: dict[str, type[Plugin]] = {}
        self._instances: dict[str, Any] = {}

    def discover_strategies(self) -> None:
        """
        Discover strategy plugins using entry points.

        Each strategy registers itself via pyproject.toml:
        [project.entry-points."power_trader.strategies"]
        my_strategy = "my_package.plugin:register"

        Raises:
            PluginError: If plugin loading fails
        """
        entry_points = importlib.metadata.entry_points()

        # Handle both old and new entry_points API
        if hasattr(entry_points, "select"):
            group = entry_points.select(group=self.ENTRY_POINT_GROUP)
        else:  # pragma: no cover - legacy entry_points() API
            group = entry_points.get(self.ENTRY_POINT_GROUP, [])  # type: ignore[arg-type]

        for entry_point in group:
            try:
                plugin = entry_point.load()
                self.register_strategy(entry_point.name, plugin)
            except Exception as e:
                raise PluginError(
                    f"Failed to load strategy plugin '{entry_point.name}': {e}"
                ) from e

    def register_strategy(self, name: str, plugin_class: type[Plugin]) -> None:
        """Manually register a strategy plugin class by name."""
        if name in self._plugins:
            raise PluginError(f"Strategy '{name}' already registered")
        self._plugins[name] = plugin_class

    def build_strategies(self, container: Container) -> None:
        """Instantiate each strategy via its own child container.

        For each plugin, a child container is created, the plugin class is
        instantiated, its ``on_register()`` is called so it registers its
        services (and itself under ``Strategy``), and the strategy is then
        resolved from that container with constructor injection.
        """
        for name, plugin_class in self._plugins.items():
            child = container.create_child()
            plugin_class().on_register(child)
            self._instances[name] = child.resolve(Strategy)

    def get_strategy(self, name: str) -> Any:
        """Get a built strategy instance by name (singleton per strategy)."""
        if name not in self._plugins:
            raise PluginError(f"Strategy '{name}' not found")
        if name not in self._instances:
            raise PluginError(
                f"Strategy '{name}' has not been built; call build_strategies() first"
            )
        return self._instances[name]

    def get_all_strategies(self) -> list[Any]:
        """Get all built strategy instances."""
        return list(self._instances.values())

    def get_strategy_names(self) -> list[str]:
        """Get names of all registered strategy plugins."""
        return list(self._plugins.keys())

    async def initialize_all(self) -> None:
        """Initialize all built strategies."""
        for strategy in self.get_all_strategies():
            if hasattr(strategy, "initialize"):
                await strategy.initialize()

    async def cleanup_all(self) -> None:
        """Clean up all built strategies."""
        for strategy in self._instances.values():
            if hasattr(strategy, "cleanup"):
                await strategy.cleanup()
