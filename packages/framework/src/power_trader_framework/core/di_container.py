"""Dependency injection container using that-depends."""

import importlib.metadata
from collections.abc import Callable
from typing import Any, TypeVar

from that_depends import BaseContainer, providers

from power_trader_framework.core.exceptions import DIError, PluginError

T = TypeVar("T")


class DIContainer(BaseContainer):
    """
    Dependency injection container.
    
    Uses that-depends for automatic constructor injection based on type hints.
    Applications extend this to register their own dependencies.
    """

    pass  # Applications will extend and add providers


class PluginRegistry:
    """
    Registry for strategy plugins.
    
    Automatically discovers and loads strategies from installed packages
    using entry points (setuptools plugin system).
    """

    ENTRY_POINT_GROUP = "power_trader.strategies"

    def __init__(self) -> None:
        self._strategies: dict[str, type] = {}
        self._initialized_instances: dict[str, Any] = {}

    def discover_strategies(self) -> None:
        """
        Discover strategies using entry points.
        
        Strategies register themselves via pyproject.toml:
        
        [project.entry-points."power_trader.strategies"]
        my_strategy = "my_package.strategy:MyStrategy"
        
        Raises:
            PluginError: If plugin loading fails
        """
        try:
            entry_points = importlib.metadata.entry_points()
            
            # Handle both old and new entry_points API
            if hasattr(entry_points, "select"):
                # Python 3.10+ API
                group = entry_points.select(group=self.ENTRY_POINT_GROUP)
            else:
                # Python 3.9 API
                group = entry_points.get(self.ENTRY_POINT_GROUP, [])
            
            for entry_point in group:
                try:
                    strategy_class = entry_point.load()
                    self.register_strategy(entry_point.name, strategy_class)
                except Exception as e:
                    raise PluginError(
                        f"Failed to load strategy '{entry_point.name}': {e}"
                    ) from e
                    
        except Exception as e:
            raise PluginError(f"Failed to discover strategies: {e}") from e

    def register_strategy(self, name: str, strategy_class: type) -> None:
        """
        Manually register a strategy.
        
        Args:
            name: Strategy name (unique identifier)
            strategy_class: Strategy class implementing IStrategy protocol
            
        Raises:
            PluginError: If strategy already registered
        """
        if name in self._strategies:
            raise PluginError(f"Strategy '{name}' already registered")
        
        self._strategies[name] = strategy_class

    def get_strategy(self, name: str) -> Any:
        """
        Get strategy instance by name.
        
        Creates instance if not already created (singleton per strategy).
        
        Args:
            name: Strategy name
            
        Returns:
            Strategy instance
            
        Raises:
            PluginError: If strategy not found
        """
        if name not in self._strategies:
            raise PluginError(f"Strategy '{name}' not found")
        
        if name not in self._initialized_instances:
            strategy_class = self._strategies[name]
            self._initialized_instances[name] = strategy_class()
        
        return self._initialized_instances[name]

    def get_all_strategies(self) -> list[Any]:
        """
        Get all registered strategy instances.
        
        Returns:
            List of strategy instances
        """
        return [self.get_strategy(name) for name in self._strategies.keys()]

    def get_strategy_names(self) -> list[str]:
        """
        Get names of all registered strategies.
        
        Returns:
            List of strategy names
        """
        return list(self._strategies.keys())

    async def initialize_all(self) -> None:
        """Initialize all registered strategies."""
        for strategy in self.get_all_strategies():
            if hasattr(strategy, "initialize"):
                await strategy.initialize()

    async def cleanup_all(self) -> None:
        """Cleanup all initialized strategies."""
        for strategy in self._initialized_instances.values():
            if hasattr(strategy, "cleanup"):
                await strategy.cleanup()


def create_factory(func: Callable[[], T]) -> providers.Factory[T]:
    """
    Helper to create a factory provider.
    
    Args:
        func: Factory function
        
    Returns:
        Factory provider
    """
    return providers.Factory(func)


def create_singleton(cls: type[T], *args: Any, **kwargs: Any) -> providers.Singleton[T]:
    """
    Helper to create a singleton provider.
    
    Args:
        cls: Class to instantiate
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Singleton provider
    """
    return providers.Singleton(cls, *args, **kwargs)
