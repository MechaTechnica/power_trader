"""Plugin registry protocol."""

from typing import Any, Protocol


class IPluginRegistry(Protocol):
    """
    Protocol for the strategy plugin registry.

    Concrete implementations (e.g. ``power_core.di_container.PluginRegistry``)
    satisfy this protocol structurally. Applications depend on this protocol
    so they never need to import a concrete registry implementation.
    """

    def discover_strategies(self) -> None:
        """Discover strategies from installed entry points."""
        ...

    def register_strategy(self, name: str, strategy_class: type) -> None:
        """Manually register a strategy class by name."""
        ...

    def get_strategy(self, name: str) -> Any:
        """Get a strategy instance by name (singleton per strategy)."""
        ...

    def get_all_strategies(self) -> list[Any]:
        """Get all registered strategy instances."""
        ...

    def get_strategy_names(self) -> list[str]:
        """Get the names of all registered strategies."""
        ...

    async def initialize_all(self) -> None:
        """Initialize all registered strategies."""
        ...

    async def cleanup_all(self) -> None:
        """Clean up all initialized strategies."""
        ...
