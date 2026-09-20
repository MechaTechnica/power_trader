"""Tests for the power-core Container (decoupled DI)."""

from typing import Protocol

import pytest

from power_core.container import Container
from power_core.exceptions import DIError
from power_framework.protocols.container import Lifetime


class Service(Protocol):
    """A service interface."""

    def run(self) -> str: ...


class DefaultService:
    """Concrete service implementation."""

    def __init__(self, name: str = "default") -> None:
        self.name = name

    def run(self) -> str:
        return f"service-{self.name}"


class Consumer:
    """Concrete object depending on the service interface."""

    def __init__(self, svc: Service) -> None:
        self.svc = svc


def test_registers_interface_and_resolves():
    container = Container()
    container.register(Service, DefaultService, name="x")
    service = container.resolve(Service)
    assert service.run() == "service-x"


def test_resolves_nested_dependency_graph():
    container = Container()
    container.register(Service, DefaultService, name="x")
    container.register(Consumer, Consumer)
    consumer = container.resolve(Consumer)
    assert consumer.svc.run() == "service-x"


def test_singleton_caches_instance():
    container = Container()
    container.register(Service, DefaultService)
    a = container.resolve(Service)
    b = container.resolve(Service)
    assert a is b


def test_transient_creates_new_each_time():
    container = Container()
    container.register(Service, DefaultService, lifetime=Lifetime.TRANSIENT)
    a = container.resolve(Service)
    b = container.resolve(Service)
    assert a is not b


def test_register_concrete_without_interface():
    container = Container()
    container.register(Service, DefaultService)
    container.register(Consumer, Consumer)
    consumer = container.resolve(Consumer)
    assert consumer.svc.run() == "service-default"


def test_register_instance_returns_same_object():
    container = Container()
    instance = DefaultService("provided")
    container.register_instance(Service, instance)
    assert container.resolve(Service) is instance


def test_duplicate_registration_raises():
    container = Container()
    container.register(Service, DefaultService)
    with pytest.raises(DIError):
        container.register(Service, Consumer)


def test_missing_dependency_raises_di_error():
    container = Container()

    class NeedsMissing:
        def __init__(self, missing: Service) -> None:
            self.missing = missing

    container.register(NeedsMissing, NeedsMissing)
    with pytest.raises(DIError):
        container.resolve(NeedsMissing)


def test_unregistered_type_raises_di_error():
    container = Container()
    with pytest.raises(DIError):
        container.resolve(Service)


def test_invalid_lifetime_raises():
    container = Container()
    with pytest.raises(DIError):
        container.register(Service, DefaultService, lifetime="bogus")


def test_generic_list_registration():
    container = Container()

    class Multi:
        def __init__(self, svcs: list[Service]) -> None:
            self.svcs = svcs

    container.register(Service, DefaultService)
    container.register(list[Service], lambda: [DefaultService("a"), DefaultService("b")])
    container.register(Multi, Multi)

    multi = container.resolve(Multi)
    assert [s.run() for s in multi.svcs] == ["service-a", "service-b"]


def test_extra_kwargs_are_passed_to_constructor():
    container = Container()
    container.register(Service, DefaultService, name="custom")
    assert container.resolve(Service).name == "custom"


@pytest.mark.asyncio
async def test_async_factory_resolution():
    container = Container()

    async def make_service() -> DefaultService:
        return DefaultService(name="async")

    container.register(Service, make_service)
    service = await container.resolve_async(Service)
    assert service.run() == "service-async"


def test_lifetime_enum_values():
    assert Lifetime.SINGLETON.value == "singleton"
    assert Lifetime.SCOPED.value == "scoped"
    assert Lifetime.TRANSIENT.value == "transient"


def test_scoped_instance_is_cached_per_scope_not_across_scopes():
    container = Container()
    container.register(Service, DefaultService, lifetime=Lifetime.SCOPED)

    with container.scope("message") as scope_a:
        first = scope_a.resolve(Service)
        assert scope_a.resolve(Service) is first

    with container.scope("message") as scope_b:
        second = scope_b.resolve(Service)
        assert second is not first


def test_scoped_resolved_from_root_behaves_like_singleton():
    container = Container()
    container.register(Service, DefaultService, lifetime=Lifetime.SCOPED)
    # The root is itself the application scope, so it caches scoped instances too.
    assert container.resolve(Service) is container.resolve(Service)


def test_named_child_container():
    container = Container(name="application")
    child = container.create_child("request")
    assert container.name == "application"
    assert child.name == "request"


def test_singleton_shared_across_scopes():
    container = Container()
    container.register(Service, DefaultService, lifetime=Lifetime.SINGLETON)

    with container.scope("message") as scope:
        a = scope.resolve(Service)
        assert scope.resolve(Service) is a
    with container.scope("message") as scope:
        assert scope.resolve(Service) is a


def test_scope_disposes_scoped_instances_on_exit():
    disposed: list[str] = []

    class Disposable:
        def close(self) -> None:
            disposed.append("closed")

    container = Container()
    container.register(Service, Disposable, lifetime=Lifetime.SCOPED)

    with container.scope("message") as scope:
        scope.resolve(Service)

    assert disposed == ["closed"]


@pytest.mark.asyncio
async def test_scope_async_disposes_scoped_instances_on_exit():
    disposed: list[str] = []

    class AsyncDisposable:
        async def stop(self) -> None:
            disposed.append("stopped")

    container = Container()
    container.register(Service, AsyncDisposable, lifetime=Lifetime.SCOPED)

    async with container.scope_async("message") as scope:
        await scope.resolve_async(Service)

    assert disposed == ["stopped"]
