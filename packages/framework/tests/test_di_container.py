"""Tests for dependency injection container."""

import pytest

from power_trader_framework.core.di_container import PluginRegistry
from power_trader_framework.core.exceptions import PluginError


class MockStrategy:
    """Mock strategy for testing."""

    @property
    def strategy_name(self) -> str:
        return "mock-strategy"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def analyze(self, bars: list) -> None:  # type: ignore
        pass

    async def initialize(self) -> None:
        self.initialized = True  # type: ignore

    async def cleanup(self) -> None:
        self.cleaned_up = True  # type: ignore


class TestPluginRegistry:
    """Tests for PluginRegistry."""

    def test_register_strategy(self) -> None:
        """Test registering a strategy."""
        registry = PluginRegistry()
        registry.register_strategy("test", MockStrategy)
        
        assert "test" in registry.get_strategy_names()

    def test_register_duplicate_raises(self) -> None:
        """Test that registering duplicate strategy raises error."""
        registry = PluginRegistry()
        registry.register_strategy("test", MockStrategy)
        
        with pytest.raises(PluginError, match="already registered"):
            registry.register_strategy("test", MockStrategy)

    def test_get_strategy(self) -> None:
        """Test getting a strategy instance."""
        registry = PluginRegistry()
        registry.register_strategy("test", MockStrategy)
        
        strategy = registry.get_strategy("test")
        assert isinstance(strategy, MockStrategy)
        assert strategy.strategy_name == "mock-strategy"

    def test_get_strategy_not_found_raises(self) -> None:
        """Test that getting nonexistent strategy raises error."""
        registry = PluginRegistry()
        
        with pytest.raises(PluginError, match="not found"):
            registry.get_strategy("nonexistent")

    def test_get_strategy_returns_singleton(self) -> None:
        """Test that get_strategy returns same instance."""
        registry = PluginRegistry()
        registry.register_strategy("test", MockStrategy)
        
        strategy1 = registry.get_strategy("test")
        strategy2 = registry.get_strategy("test")
        
        assert strategy1 is strategy2

    def test_get_all_strategies(self) -> None:
        """Test getting all strategy instances."""
        registry = PluginRegistry()
        registry.register_strategy("test1", MockStrategy)
        registry.register_strategy("test2", MockStrategy)
        
        strategies = registry.get_all_strategies()
        assert len(strategies) == 2

    async def test_initialize_all(self) -> None:
        """Test initializing all strategies."""
        registry = PluginRegistry()
        registry.register_strategy("test", MockStrategy)
        
        await registry.initialize_all()
        
        strategy = registry.get_strategy("test")
        assert hasattr(strategy, "initialized")
        assert strategy.initialized  # type: ignore

    async def test_cleanup_all(self) -> None:
        """Test cleaning up all strategies."""
        registry = PluginRegistry()
        registry.register_strategy("test", MockStrategy)
        
        # Initialize first so instance is created
        await registry.initialize_all()
        await registry.cleanup_all()
        
        strategy = registry.get_strategy("test")
        assert hasattr(strategy, "cleaned_up")
        assert strategy.cleaned_up  # type: ignore
