"""Dependency injection container abstract base class and binding lifetime."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from enum import StrEnum
from typing import Any, TypeVar, overload

T_co = TypeVar("T_co", covariant=True)


class Lifetime(StrEnum):
    """How long a registered binding lives before it is recreated."""

    SINGLETON = "singleton"
    """One instance shared by the whole application (the root container)."""

    SCOPED = "scoped"
    """One instance per scope (child container), e.g. per request/message/job."""

    TRANSIENT = "transient"
    """A fresh instance on every resolve."""

#todo: Don't pass the Container directly to applications register method becuase it allows applications to resolve, while they should only be concerted about registering
class Container(ABC):
    """
    Abstract base for a dependency injection container.

    Concrete implementations (e.g. ``power_core.container.Container``)
    subclass this ABC, so a missing member is caught at import time rather than
    silently at a call site. Applications depend on this ABC so they never need
    to import a concrete container implementation.

    Containers form a hierarchy: the root is the *application scope* and
    :meth:`create_child` (or the :meth:`scope` context managers) produce
    nested *request*, *message*, or *job* scopes. ``Lifetime.SINGLETON``
    bindings are cached on the root, ``Lifetime.SCOPED`` bindings are cached
    on the scope that resolves them, and ``Lifetime.TRANSIENT`` bindings are
    never cached.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The human-readable name of this container/scope."""

    @abstractmethod
    def create_child(self, name: str = "child") -> "Container":
        """Create a child scope that falls back to this container for lookups.

        Scoped bindings resolved through the child are cached on the child, so
        each child gets its own instances (e.g. a distinct correlation ID or
        transaction context per message).
        """

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

    @overload
    def register(
        self,
        interface: Any,
        *,
        lifetime: Lifetime = Lifetime.SINGLETON,
    ) -> None:
        """Register a concrete type to itself."""

    @abstractmethod
    def register(
        self,
        interface: Any,
        implementation: Any = None,
        *,
        lifetime: Lifetime = Lifetime.SINGLETON,
        **kwargs: Any,
    ) -> None:
        """Register an implementation (class or factory) against an interface."""

    @overload
    def register_instance(self, interface: Any, instance: Callable[[], Any]) -> None:
        """Register a lazy zero-arg factory, e.g. ``lambda: make_thing()``."""

    @overload
    def register_instance(self, interface: Any, instance: Any) -> None:
        """Register an already-constructed instance."""
        ...

    @abstractmethod
    def register_instance(self, interface: Any, instance: Any) -> None:
        """Register an already-constructed instance or a lazy factory."""

    @abstractmethod
    def override(self, interface: Any, instance: Any) -> None:
        """Replace any registration for ``interface`` with an instance.

        This is the *test seam* backing
        ``TestApplicationBuilder.replace(Interface, Fake())``: it substitutes an
        installed adapter for a fake without editing production wiring.
        """

    @abstractmethod
    def validate(self, *roots: Any) -> None:
        """Validate that every root's dependency graph is fully resolvable.

        Raises ``FrameworkError`` when a dependency has no registration, with a
        human-readable tree in the message.
        """

    @abstractmethod
    def validate_report(self, *roots: Any) -> str:
        """Return the validation report for ``*roots`` as a formatted string."""

    @overload
    def resolve(self, interface: type[T_co]) -> T_co: ...

    @overload
    def resolve(self, interface: type[Any]) -> Any: ...

    @abstractmethod
    def resolve(self, interface: type[Any]) -> Any:
        """Resolve ``interface``, building its dependency graph."""

    @abstractmethod
    def resolve_all(self, interface: Any) -> list[Any]:
        """Resolve every registered implementation of ``interface``.

        Matches registrations whose unparameterized origin equals ``interface``,
        so ``resolve_all(Strategy)`` returns every ``Strategy[T]`` specialization.
        """

    @abstractmethod
    async def resolve_async(self, interface: type[Any]) -> Any:
        """Resolve ``interface``, awaiting any async factory hooks."""

    @abstractmethod
    def scope(self, name: str = "scope") -> AbstractContextManager["Container"]:
        """Yield a child scope and dispose its scoped instances on exit."""

    @abstractmethod
    def scope_async(self, name: str = "scope") -> AbstractAsyncContextManager["Container"]:
        """Yield a child scope and async-dispose its scoped instances on exit."""

    @abstractmethod
    def dispose(self) -> None:
        """Dispose (synchronously) every instance cached by this scope."""

    @abstractmethod
    async def dispose_async(self) -> None:
        """Dispose (asynchronously) every instance cached by this scope."""