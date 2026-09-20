"""Lifecycle protocol for components owned by the runtime."""

from typing import Any, Protocol


class Lifecycle(Protocol):
    """A component whose start/stop lifecycle is owned by the runtime.

    Every long-lived component (infrastructure adapters, domain services,
    extensions, and the application itself) exposes the same two hooks. The
    runtime drives ``start`` in dependency order and ``stop`` in reverse,
    removing the need for individual components to coordinate each other.
    """

    async def start(self) -> None:
        """Prepare the component for use (connect, initialize, warm up)."""
        ...

    async def stop(self) -> None:
        """Release the component's resources (disconnect, clean up)."""
        ...


class LifecycleRegistry(Protocol):
    """Collects lifecycle component types in start order.

    Plugins register the *interface* of each lifecycle component during wiring.
    This is only the registration surface; the runtime is responsible for
    resolving and driving the registered components.
    """

    def register(self, component_type: type[Any]) -> None:
        """Register a lifecycle component type, in start order."""
        ...
