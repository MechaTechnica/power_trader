"""Dependency injection container protocol."""

from typing import Any, Protocol, TypeVar, overload

T = TypeVar("T", covariant=True)


class IContainer(Protocol):
    """
    Protocol for a dependency injection container.

    Concrete implementations (e.g. ``power_core.container.Container``)
    satisfy this protocol structurally. Applications depend on this protocol
    so they never need to import a concrete container implementation.
    """

    def register(
        self,
        interface: type[Any],
        implementation: Any = None,
        *,
        lifetime: str = "singleton",
        **kwargs: Any,
    ) -> None:
        """Register an implementation against an interface type."""
        ...

    def register_instance(self, interface: type[Any], instance: Any) -> None:
        """Register an already-constructed instance."""
        ...

    @overload
    def resolve(self, interface: type[T]) -> T: ...

    @overload
    def resolve(self, interface: type[Any]) -> Any: ...

    def resolve(self, interface: type[Any]) -> Any:
        """Resolve ``interface``, building its dependency graph."""
        ...

    async def resolve_async(self, interface: type[Any]) -> Any:
        """Resolve ``interface``, awaiting any async factory hooks."""
        ...
