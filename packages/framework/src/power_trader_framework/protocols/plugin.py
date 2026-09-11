"""Strategy plugin registry protocols."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    from power_trader_framework.plugins import Plugin
    from power_trader_framework.protocols.container import Container
    from power_trader_framework.protocols.strategy import Strategy


class PluginRegistry(Protocol):
    """Registry for discovering, building, and looking up strategy plugins.

    The registry owns strategy *composition* (discovery, registration, and
    construction) and *lookup*. Applications depend only on this protocol and
    never on a concrete registry implementation. Lifecycle (``initialize`` /
    ``cleanup``) is expressed separately via :class:`StrategyLifecycle`.
    """

    def discover(self) -> tuple[str, ...]:
        """Discover installed strategy plugins and return newly added names.

        Discovery is idempotent, allowing applications and tests to invoke it
        safely more than once.
        """
        ...

    def register(self, name: str, plugin_class: type[Plugin]) -> None:
        """Register a strategy plugin class under ``name``.

        Raises:
            PluginError: If ``name`` is already registered.
        """
        ...

    def build(self, container: Container) -> None:
        """Build all registered strategies using dependency injection.

        Each strategy is constructed in its own child container; the plugin's
        ``register()`` is called so it binds its dependencies (and itself under
        ``Strategy``), then the strategy is resolved with constructor injection.
        Instances are retained and are singletons for the registry's lifetime.
        """
        ...

    def get(self, name: str) -> Strategy:
        """Return the built strategy registered under ``name``.

        Raises:
            PluginError: If ``name`` is not registered or not yet built.
        """
        ...

    def get_all(self) -> Sequence[Strategy]:
        """Return all built strategies in registration order."""
        ...

    def names(self) -> Sequence[str]:
        """Return registered strategy names in registration order."""
        ...


class StrategyLifecycle(Protocol):
    """Protocol for initializing and cleaning up built strategies."""

    async def initialize(self) -> None:
        """Initialize all built strategies."""
        ...

    async def cleanup(self) -> None:
        """Clean up all built strategies."""
        ...
