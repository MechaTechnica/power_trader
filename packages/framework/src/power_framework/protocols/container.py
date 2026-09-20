"""Dependency injection container protocol."""

from collections.abc import AsyncIterator, Callable, Iterator
from enum import StrEnum
from typing import Any, Protocol, TypeVar, overload

T_co = TypeVar("T_co", covariant=True)


class Lifetime(StrEnum):
    """How long a registered binding lives before it is recreated.

    This replaces ad-hoc ``"singleton"`` / ``"transient"`` strings with a
    single, self-documenting vocabulary shared by the framework contract and
    the concrete runtime.
    """

    SINGLETON = "singleton"
    """One instance shared by the whole application (the root container)."""

    SCOPED = "scoped"
    """One instance per scope (child container), e.g. per request/message/job."""

    TRANSIENT = "transient"
    """A fresh instance on every resolve."""


class Container(Protocol):
    """
    Protocol for a dependency injection container.

    Concrete implementations (e.g. ``power_core.container.Container``)
    satisfy this protocol structurally. Applications depend on this protocol
    so they never need to import a concrete container implementation.

    Containers form a hierarchy: the root is the *application scope* and
    :meth:`create_child` (or the :meth:`scope` context managers) produce
    nested *request*, *message*, or *job* scopes. ``Lifetime.SINGLETON``
    bindings are cached on the root, ``Lifetime.SCOPED`` bindings are cached
    on the scope that resolves them, and ``Lifetime.TRANSIENT`` bindings are
    never cached.
    """

    @property
    def name(self) -> str:
        """The human-readable name of this container/scope."""
        ...

    def create_child(self, name: str = "child") -> "Container":
        """Create a child scope that falls back to this container for lookups.

        Scoped bindings resolved through the child are cached on the child, so
        each child gets its own instances (e.g. a distinct correlation ID or
        transaction context per message).
        """
        ...

    @overload
    def register(
        self,
        interface: Any,
        implementation: type[Any],
        *,
        lifetime: Lifetime = Lifetime.SINGLETON,
        **kwargs: Any,
    ) -> None:
        """Register a concrete class (constructor-injected)."""
        ...

    @overload
    def register(
        self,
        interface: Any,
        implementation: Callable[..., Any],
        *,
        lifetime: Lifetime = Lifetime.SINGLETON,
        **kwargs: Any,
    ) -> None:
        """Register a factory callable, e.g. ``lambda: make_thing()``."""
        ...

    @overload
    def register(
        self,
        interface: Any,
        *,
        lifetime: Lifetime = Lifetime.SINGLETON,
    ) -> None:
        """Register a concrete type to itself."""
        ...

    def register(
        self,
        interface: Any,
        implementation: Any = None,
        *,
        lifetime: Lifetime = Lifetime.SINGLETON,
        **kwargs: Any,
    ) -> None:
        """Register an implementation (class or factory) against an interface."""
        ...

    @overload
    def register_instance(self, interface: Any, instance: Callable[[], Any]) -> None:
        """Register a lazy zero-arg factory, e.g. ``lambda: make_thing()``."""
        ...

    @overload
    def register_instance(self, interface: Any, instance: Any) -> None:
        """Register an already-constructed instance."""
        ...

    def register_instance(self, interface: Any, instance: Any) -> None:
        """Register an already-constructed instance or a lazy factory."""
        ...

    def override(self, interface: Any, instance: Any) -> None:
        """Replace any registration for ``interface`` with an instance.

        This is the *test seam* backing
        ``TestApplicationBuilder.replace(Interface, Fake())``: it substitutes an
        installed adapter for a fake without editing production wiring.
        """
        ...

    def validate(self, *roots: Any) -> None:
        """Validate that every root's dependency graph is fully resolvable.

        Raises ``DependencyValidationError`` when a dependency has no
        registration, with a human-readable tree in the message.
        """
        ...

    def validate_report(self, *roots: Any) -> str:
        """Return the validation report for ``*roots`` as a formatted string."""
        ...

    @overload
    def resolve(self, interface: type[T_co]) -> T_co: ...

    @overload
    def resolve(self, interface: type[Any]) -> Any: ...

    def resolve(self, interface: type[Any]) -> Any:
        """Resolve ``interface``, building its dependency graph."""
        ...

    def resolve_all(self, interface: Any) -> list[Any]:
        """Resolve every registered implementation of ``interface``.

        Matches registrations whose unparameterized origin equals ``interface``,
        so ``resolve_all(Strategy)`` returns every ``Strategy[T]`` specialization.
        """
        ...

    async def resolve_async(self, interface: type[Any]) -> Any:
        """Resolve ``interface``, awaiting any async factory hooks."""
        ...

    def scope(self, name: str = "scope") -> Iterator["Container"]:
        """Yield a child scope and dispose its scoped instances on exit."""
        ...

    def scope_async(self, name: str = "scope") -> AsyncIterator["Container"]:
        """Yield a child scope and async-dispose its scoped instances on exit."""
        ...

    def dispose(self) -> None:
        """Dispose (synchronously) every instance cached by this scope."""
        ...

    async def dispose_async(self) -> None:
        """Dispose (asynchronously) every instance cached by this scope."""
        ...
