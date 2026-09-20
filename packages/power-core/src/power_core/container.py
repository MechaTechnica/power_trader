"""Decoupled dependency injection container.

A plain ``Container`` maps *interface types* to lazy *implementations*.
Resolving a type builds its dependency chain automatically from constructor
type hints, so adapters and use cases never need to know about the container
itself.

Usage
-----
>>> container = Container()
>>> container.register(SignalAggregator, WeightedAverageAggregator)
>>> container.register(MarketDataProvider, InteractiveBrokersAdapter,
...                    host="127.0.0.1", port=7497, client_id=1)
>>> container.register(OutputPresenter, TerminalOutputAdapter)
>>> container.register(MonitorStocksUseCase, MonitorStocksUseCase)
>>> container.register(CLIAdapter, CLIAdapter)
>>>
>>> cli: CLIAdapter = container.resolve(CLIAdapter)

Scopes & lifetimes
------------------
A container is hierarchical: the root container is the *application scope* and
:meth:`Container.create_child` (or the :meth:`Container.scope` context
managers) produces nested *request*, *message*, or *job* scopes. A binding's
:class:`Lifetime` controls where its instance is cached:

- ``Lifetime.SINGLETON`` (default): one instance per application, cached on the
  container that registered it.
- ``Lifetime.SCOPED``: one instance per scope. Resolved through a child it is
  cached on that child, so each message/job gets its own correlation ID,
  transaction context, and request services.
- ``Lifetime.TRANSIENT``: a new instance on every resolve.

For example, in a bank application::

    app = Container(name="application")
    app.register(AccountRepository, SqlAccountRepository)      # singleton
    app.register(UnitOfWork, UnitOfWork, lifetime=Lifetime.SCOPED)

    with app.scope("message") as scope:                        # message #1
        uow1 = scope.resolve(UnitOfWork)
        assert scope.resolve(UnitOfWork) is uow1               # cached per scope
    with app.scope("message") as scope:                        # message #2
        uow2 = scope.resolve(UnitOfWork)
        assert uow2 is not uow1                                # distinct per message
"""

import inspect
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import Any, TypeVar, get_args, get_origin, overload

from power_core.exceptions import DIError
from power_framework.protocols.container import Lifetime

T = TypeVar("T")

#: Optional concrete implementation type registered alongside an interface.
Implementation = type[Any] | Callable[..., Any] | None

#: Sentinel for "no instance yet".
_UNSET = object()


def _type_name(t: Any) -> str:
    """Return a human-readable name for a type or generic alias."""
    origin = get_origin(t)
    if origin is not None:
        return getattr(origin, "__name__", str(origin))
    return getattr(t, "__name__", str(t))


def _origin_of(t: Any) -> Any:
    """Return the unparameterized origin of ``t`` (or ``t`` itself)."""
    origin = get_origin(t)
    return origin if origin is not None else t


def _coerce_lifetime(lifetime: Lifetime | str) -> Lifetime:
    """Normalise a ``Lifetime`` (or a legacy string) to the enum form."""
    if isinstance(lifetime, Lifetime):
        return lifetime
    try:
        return Lifetime(lifetime)
    except ValueError:
        valid = ", ".join(f"'{member.value}'" for member in Lifetime)
        raise DIError(
            f"Invalid lifetime '{lifetime}' (expected one of: {valid})"
        ) from None


#: Generic collection origins auto-resolved as a list of their items.
_COLLECTION_ORIGINS = (list, tuple, set, frozenset)

#: Sync teardown hooks tried, in order, when disposing a scoped instance.
_SYNC_DISPOSE_HOOKS = ("dispose", "close", "stop")
#: Async teardown hooks tried, in order, when async-disposing a scoped instance.
_ASYNC_DISPOSE_HOOKS = ("aclose", "stop", "dispose", "close")


@dataclass
class Registration:
    """A registered interface -> implementation binding."""

    interface: type[Any]
    implementation: Implementation
    lifetime: Lifetime = Lifetime.SINGLETON
    extra_kwargs: dict[str, Any] = field(default_factory=dict)
    instance: Any = _UNSET  # cached singleton instance


class Container:
    """Registry that resolves dependency graphs by type.

    Containers form a parent/child hierarchy. Scoped bindings are cached on the
    container that first resolves them, which is what gives each child scope its
    own set of request/message/job-scoped instances.
    """

    def __init__(self, parent: "Container | None" = None, name: str = "root") -> None:
        self._registry: dict[type[Any], Registration] = {}
        self._parent = parent
        self._name = name
        #: interface -> instance cache for ``Lifetime.SCOPED`` bindings. Scoped
        #: instances live on the *resolving* container, not the one that
        #: registered them, so each child scope gets its own copies.
        self._scoped_cache: dict[type[Any], Any] = {}

    @property
    def name(self) -> str:
        """The human-readable name of this container/scope."""
        return self._name

    def create_child(self, name: str = "child") -> "Container":
        """Create a child scope that falls back to this container for lookups.

        Scoped bindings resolved through the child are cached on the child, so
        each child gets its own instances (e.g. a distinct correlation ID or
        transaction context per message/job).
        """
        return Container(parent=self, name=name)

    def __repr__(self) -> str:
        return f"<Container name={self._name!r} registrations={len(self._registry)}>"

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    @overload
    def register(
        self,
        interface: type[Any],
        implementation: type[Any],
        *,
        lifetime: Lifetime | str = Lifetime.SINGLETON,
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
        lifetime: Lifetime | str = Lifetime.SINGLETON,
        **kwargs: Any,
    ) -> None:
        """Register a factory callable, e.g. ``lambda: make_thing()``."""
        ...

    @overload
    def register(
        self,
        interface: type[Any],
        *,
        lifetime: Lifetime | str = Lifetime.SINGLETON,
    ) -> None:
        """Register a concrete type to itself."""
        ...

    def register(
        self,
        interface: type[Any],
        implementation: Implementation = None,
        *,
        lifetime: Lifetime | str = Lifetime.SINGLETON,
        **kwargs: Any,
    ) -> None:
        """Register an implementation against an interface type.

        ``implementation`` may be either a concrete class (its constructor is
        dependency-injected) or a factory callable (invoked with ``**kwargs``).
        When omitted, ``interface`` itself is registered.

        Args:
            interface: The type other objects depend on (protocol or concrete class).
            implementation: The class/factory used to build the instance. Defaults to
                ``interface`` when omitted (registering a concrete type).
            lifetime: ``Lifetime.SINGLETON``, ``Lifetime.SCOPED``, or
                ``Lifetime.TRANSIENT`` (legacy ``"singleton"``/``"scoped"``/
                ``"transient"`` strings are also accepted).
            **kwargs: Extra keyword arguments passed to the constructor/factory.

        Raises:
            DIError: If ``interface`` is already registered or ``lifetime`` is invalid.
        """
        if interface in self._registry:
            raise DIError(f"Type '{_type_name(interface)}' is already registered")

        impl = implementation if implementation is not None else interface
        self._registry[interface] = Registration(
            interface=interface,
            implementation=impl,
            lifetime=_coerce_lifetime(lifetime),
            extra_kwargs=kwargs,
        )

    @overload
    def register_instance(self, interface: type[Any], instance: Callable[[], Any]) -> None:
        """Register a lazy zero-arg factory, e.g. ``lambda: make_thing()``."""
        ...

    @overload
    def register_instance(self, interface: type[Any], instance: Any) -> None:
        """Register an already-constructed instance."""
        ...

    def register_instance(self, interface: type[Any], instance: Any) -> None:
        """Register an already-constructed instance or a lazy factory.

        When ``instance`` is callable (a zero-arg factory such as
        ``lambda: make_thing()``) it is stored as a lazily-constructed
        singleton; otherwise ``instance`` is stored directly as an eager
        singleton (useful for mocks/config).

        Raises:
            DIError: If ``interface`` is already registered.
        """
        if interface in self._registry:
            raise DIError(f"Type '{_type_name(interface)}' is already registered")

        if callable(instance) and not isinstance(instance, type):
            # Lazy factory: construct on first resolve, then cache.
            self._registry[interface] = Registration(
                interface=interface,
                implementation=instance,
                lifetime=Lifetime.SINGLETON,
            )
            return

        reg = Registration(
            interface=interface,
            implementation=lambda: instance,
            lifetime=Lifetime.SINGLETON,
        )
        reg.instance = instance
        self._registry[interface] = reg

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------
    @overload
    def resolve(self, interface: type[T]) -> T: ...

    @overload
    def resolve(self, interface: type[Any]) -> Any: ...

    def resolve(self, interface: type[Any]) -> Any:
        """Resolve ``interface`` synchronously, building its dependency graph.

        ``interface`` may be a Protocol or a concrete class.

        Raises:
            DIError: If a dependency type cannot be satisfied.
        """
        reg = self._get_registration(interface)
        if reg.lifetime is Lifetime.SINGLETON and reg.instance is not _UNSET:
            return reg.instance
        if reg.lifetime is Lifetime.SCOPED:
            cached = self._scoped_cache.get(reg.interface, _UNSET)
            if cached is not _UNSET:
                return cached

        instance = self._construct(reg.interface, reg.implementation, reg.extra_kwargs)
        if reg.lifetime is Lifetime.SINGLETON:
            reg.instance = instance
        elif reg.lifetime is Lifetime.SCOPED:
            self._scoped_cache[reg.interface] = instance
        return instance

    @overload
    async def resolve_async(self, interface: type[T]) -> T: ...

    @overload
    async def resolve_async(self, interface: type[Any]) -> Any: ...

    async def resolve_async(self, interface: type[Any]) -> Any:
        """Resolve ``interface``, awaiting any async factory/constructor hooks.

        Aspects of the object graph that require awaiting (e.g. ``connect()``,
        ``initialize()``) can be handled by factories registered with
        ``register(...)`` returning a coroutine function. This method resolves
        the graph like :meth:`resolve` but supports transient async factories.
        """
        reg = self._get_registration(interface)
        if reg.lifetime is Lifetime.SINGLETON and reg.instance is not _UNSET:
            return reg.instance
        if reg.lifetime is Lifetime.SCOPED:
            cached = self._scoped_cache.get(reg.interface, _UNSET)
            if cached is not _UNSET:
                return cached

        instance = await self._construct_async(
            reg.interface, reg.implementation, reg.extra_kwargs
        )
        if reg.lifetime is Lifetime.SINGLETON:
            reg.instance = instance
        elif reg.lifetime is Lifetime.SCOPED:
            self._scoped_cache[reg.interface] = instance
        return instance

    def resolve_all(self, interface: Any) -> list[Any]:
        """Resolve every registered implementation of ``interface``.

        Matches registrations whose *unparameterized origin* equals
        ``interface``, so ``resolve_all(Strategy)`` returns every
        ``Strategy[T]`` specialization in registration order. Useful for
        injecting ``list[Strategy]`` (or another collection) of plugins.
        """
        instances: list[Any] = []
        for key in self._registry:
            if _origin_of(key) is interface:
                instances.append(self.resolve(key))
        if self._parent is not None:
            instances.extend(self._parent.resolve_all(interface))
        return instances

    # ------------------------------------------------------------------
    # Scopes
    # ------------------------------------------------------------------
    @contextmanager
    def scope(self, name: str = "scope") -> Iterator["Container"]:
        """Yield a child scope and dispose its scoped instances on exit.

        Usage::

            with app.scope("message") as scope:
                uow = scope.resolve(UnitOfWork)
        """
        child = self.create_child(name)
        try:
            yield child
        finally:
            child.dispose()

    @asynccontextmanager
    async def scope_async(self, name: str = "scope") -> AsyncIterator["Container"]:
        """Yield a child scope and async-dispose its scoped instances on exit.

        Usage::

            async with app.scope_async("message") as scope:
                uow = await scope.resolve_async(UnitOfWork)
        """
        child = self.create_child(name)
        try:
            yield child
        finally:
            await child.dispose_async()

    def dispose(self) -> None:
        """Dispose (synchronously) every instance cached by this scope.

        Scoped instances are disposed in reverse resolution order using the
        first available sync hook among ``dispose``/``close``/``stop``.
        """
        for instance in reversed(list(self._scoped_cache.values())):
            self._dispose_sync(instance)
        self._scoped_cache.clear()

    async def dispose_async(self) -> None:
        """Dispose (asynchronously) every instance cached by this scope.

        Scoped instances are disposed in reverse resolution order using the
        first available async hook among ``aclose``/``stop``/``dispose``/
        ``close``.
        """
        for instance in reversed(list(self._scoped_cache.values())):
            await self._dispose_async(instance)
        self._scoped_cache.clear()

    @staticmethod
    def _dispose_sync(instance: Any) -> None:
        for hook in _SYNC_DISPOSE_HOOKS:
            fn = getattr(instance, hook, None)
            if not callable(fn):
                continue
            try:
                result = fn()
            except Exception:
                return
            if not inspect.isawaitable(result):
                return
            # Awaitable in a sync context: fall through to other hooks.
        return

    @staticmethod
    async def _dispose_async(instance: Any) -> None:
        for hook in _ASYNC_DISPOSE_HOOKS:
            fn = getattr(instance, hook, None)
            if not callable(fn):
                continue
            try:
                result = fn()
            except Exception:
                return
            if inspect.isawaitable(result):
                await result
            return

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _has_registration(self, interface: Any) -> bool:
        if interface in self._registry:
            return True
        if self._parent is not None:
            return self._parent._has_registration(interface)
        return False

    def _get_registration(self, interface: type[Any]) -> Registration:
        if interface in self._registry:
            return self._registry[interface]
        if self._parent is not None:
            return self._parent._get_registration(interface)
        # Allow unregistered concrete types to self-register if resolvable.
        raise DIError(
            f"No registration for type '{_type_name(interface)}'. "
            f"Call container.register({_type_name(interface)}, <implementation>) first."
        )

    def _construct(
        self,
        interface: type[Any],
        impl: Implementation,
        extra_kwargs: dict[str, Any],
    ) -> Any:
        """Build ``impl`` synchronously, resolving dependencies by type."""
        try:
            params = self._inspect_params(impl)
        except (TypeError, ValueError):
            raise DIError(
                f"Cannot inspect constructor for '{getattr(impl, '__name__', str(impl))}'"
            ) from None

        kwargs = dict(extra_kwargs)
        missing: list[str] = []
        for name, annotation in params.items():
            if name in kwargs:
                continue
            if get_origin(annotation) in _COLLECTION_ORIGINS:
                if self._has_registration(annotation):
                    kwargs[name] = self.resolve(annotation)
                else:
                    kwargs[name] = self._resolve_collection(annotation)
                continue
            if annotation in (Any, inspect.Parameter.empty) or annotation is None:
                raise DIError(
                    f"Parameter '{name}' of '{getattr(impl, '__name__', str(impl))}' "
                    "is untyped and cannot be auto-resolved"
                )
            try:
                kwargs[name] = self.resolve(annotation)
            except DIError:
                # Not registered -> inject interface itself if it equals ctor param type.
                if annotation is interface:
                    kwargs[name] = self._construct(interface, impl, extra_kwargs)
                else:
                    missing.append(f"{name}: {getattr(annotation, '__name__', str(annotation))}")

        if missing:
            raise DIError(
                f"Unresolvable dependencies for '{getattr(impl, '__name__', str(impl))}': "
                + ", ".join(missing)
            )

        try:
            return self._resolve_ctor(impl)(**kwargs)
        except Exception as e:
            raise DIError(
                f"Failed to construct '{getattr(impl, '__name__', str(impl))}': {e}"
            ) from e

    async def _construct_async(
        self,
        interface: type[Any],
        impl: Implementation,
        extra_kwargs: dict[str, Any],
    ) -> Any:
        """Build ``impl`` asynchronously, awaiting nested async factories."""
        try:
            params = self._inspect_params(impl)
        except (TypeError, ValueError):
            raise DIError(
                f"Cannot inspect constructor for '{getattr(impl, '__name__', str(impl))}'"
            ) from None

        kwargs = dict(extra_kwargs)
        missing: list[str] = []
        for name, annotation in params.items():
            if name in kwargs:
                continue
            if get_origin(annotation) in _COLLECTION_ORIGINS:
                if self._has_registration(annotation):
                    kwargs[name] = await self.resolve_async(annotation)
                else:
                    kwargs[name] = self._resolve_collection(annotation)
                continue
            if annotation in (Any, inspect.Parameter.empty) or annotation is None:
                raise DIError(
                    f"Parameter '{name}' of '{getattr(impl, '__name__', str(impl))}' "
                    "is untyped and cannot be auto-resolved"
                )
            try:
                kwargs[name] = await self.resolve_async(annotation)
            except DIError:
                if annotation is interface:
                    kwargs[name] = await self._construct_async(interface, impl, extra_kwargs)
                else:
                    missing.append(f"{name}: {getattr(annotation, '__name__', str(annotation))}")

        if missing:
            raise DIError(
                f"Unresolvable dependencies for '{getattr(impl, '__name__', str(impl))}': "
                + ", ".join(missing)
            )

        result = self._resolve_ctor(impl)(**kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    def _resolve_collection(self, annotation: Any) -> Any:
        """Resolve a collection annotation by gathering all item registrations."""
        (item_type,) = get_args(annotation)
        items = self.resolve_all(item_type)
        return get_origin(annotation)(items)

    @staticmethod
    def _resolve_ctor(impl: Implementation) -> Callable[..., Any]:
        # Classes instantiate via impl(**kwargs) (signature excludes 'self');
        # plain callables/factories are invoked directly.
        assert impl is not None
        return impl

    @staticmethod
    def _inspect_params(impl: Implementation) -> dict[str, Any]:
        """Return a name -> annotation map of the injectable constructor params.

        Only parameters *without* defaults are injected; parameters with defaults
        (e.g. scalars like ``name="default"``) use their default value.
        """
        # For a class, inspect.signature(cls) gives the __init__ params minus 'self'.
        assert impl is not None
        sig = inspect.signature(impl)
        params: dict[str, Any] = {}
        for name, param in sig.parameters.items():
            if name in ("self",):
                continue
            if param.default is not inspect.Parameter.empty:
                continue  # has a default -> use the default, don't inject
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue  # *args / **kwargs are not injected
            annot = param.annotation
            params[name] = annot if annot is not inspect.Parameter.empty else Any
        return params
