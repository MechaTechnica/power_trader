"""Plugin registry protocol."""

from typing import Any, Protocol

from power_trader_framework.plugins import PluginBase
from power_trader_framework.protocols.container import IContainer


class IPluginRegistry(Protocol):
    """
    Protocol for the strategy plugin registry.

    Concrete implementations (e.g. ``power_core.di_container.PluginRegistry``)
    satisfy this protocol structurally. Applications depend on this protocol
    so they never need to import a concrete registry implementation.
    """

    def discover_strategies(self) -> None:
        """Discover strategy plugin classes from installed entry points."""
        ...

    def build_strategies(self, container: IContainer) -> None:
        """Instantiate each discovered plugin and build its strategy.

        For each plugin, a child container is created, the plugin's
        ``on_register()`` is called so it registers its services (and itself
        under ``IStrategy``), and the strategy is then resolved
        (constructor-injected) from that container.
        """
        ...

    def register_strategy(self, name: str, plugin_class: type[PluginBase]) -> None:
        """Manually register a strategy plugin class by name."""
        ...

    def get_strategy(self, name: str) -> Any:
        """Get a built strategy instance by name (singleton per strategy)."""
        ...

    def get_all_strategies(self) -> list[Any]:
        """Get all built strategy instances."""
        ...

    def get_strategy_names(self) -> list[str]:
        """Get the names of all registered strategy plugins."""
        ...

    async def initialize_all(self) -> None:
        """Initialize all built strategies."""
        ...

    async def cleanup_all(self) -> None:
        """Clean up all built strategies."""
        ...
