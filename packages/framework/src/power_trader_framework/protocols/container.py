"""Dependency injection container protocol."""

from collections.abc import Callable
from typing import Any, Protocol, TypeVar, overload

T = TypeVar("T", covariant=True)


class IContainer(Protocol):
    """
    Protocol for a dependency injection container.

    Concrete implementations (e.g. ``power_core.container.Container``)
    satisfy this protocol structurally. Applications depend on this protocol
    so they never need to import a concrete container implementation.
    """

    @overload
    def register(
        self,
        interface: type[Any],
        implementation: type[Any],
        *,
        lifetime: str = "singleton",
        **kwargs: Any,
    ) -> None:
        """Register a concrete class (constructor-injected)."""
        ...

    @overload
    def register(
        self,
        interface: type[Any],
        implementation: Callable[..., Any],
        *,
        lifetime: str = "singleton",
        **kwargs: Any,
    ) -> None:
        """Register a factory callable, e.g. ``lambda: make_thing()``."""
        ...

    @overload
    def register(
        self,
        interface: type[Any],
        *,
        lifetime: str = "singleton",
    ) -> None:
        """Register a concrete type to itself."""
        ...

    def register(
        self,
        interface: type[Any],
        implementation: Any = None,
        *,
        lifetime: str = "singleton",
        **kwargs: Any,
    ) -> None:
        """Register an implementation (class or factory) against an interface."""
        ...

    @overload
    def register_instance(self, interface: type[Any], instance: Callable[[], Any]) -> None:
        """Register a lazy zero-arg factory, e.g. ``lambda: make_thing()``."""
        ...

    @overload
    def register_instance(self, interface: type[Any], instance: Any) -> None:
        """Register an already-constructed instance."""
        ...

    def register_instance(self, interface: type[Any], instance: Any) -> None:
        """Register an already-constructed instance or a lazy factory."""
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
