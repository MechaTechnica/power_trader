"""Tests for the power-core Container (decoupled DI)."""

from typing import Protocol

import pytest
from power_core.container import Container
from power_core.exceptions import DIError


class IService(Protocol):
    """A service interface."""

    def run(self) -> str: ...


class Service:
    """Concrete service implementation."""

    def __init__(self, name: str = "default") -> None:
        self.name = name

    def run(self) -> str:
        return f"service-{self.name}"


class Consumer:
    """Concrete object depending on the service interface."""

    def __init__(self, svc: IService) -> None:
        self.svc = svc


def test_registers_interface_and_resolves():
    container = Container()
    container.register(IService, Service, name="x")
    service = container.resolve(IService)
    assert service.run() == "service-x"


def test_resolves_nested_dependency_graph():
    container = Container()
    container.register(IService, Service, name="x")
    container.register(Consumer, Consumer)
    consumer = container.resolve(Consumer)
    assert consumer.svc.run() == "service-x"


def test_singleton_caches_instance():
    container = Container()
    container.register(IService, Service)
    a = container.resolve(IService)
    b = container.resolve(IService)
    assert a is b


def test_transient_creates_new_each_time():
    container = Container()
    container.register(IService, Service, lifetime="transient")
    a = container.resolve(IService)
    b = container.resolve(IService)
    assert a is not b


def test_register_concrete_without_interface():
    container = Container()
    container.register(IService, Service)
    container.register(Consumer, Consumer)
    consumer = container.resolve(Consumer)
    assert consumer.svc.run() == "service-default"


def test_register_instance_returns_same_object():
    container = Container()
    instance = Service("provided")
    container.register_instance(IService, instance)
    assert container.resolve(IService) is instance


def test_duplicate_registration_raises():
    container = Container()
    container.register(IService, Service)
    with pytest.raises(DIError):
        container.register(IService, Consumer)


def test_missing_dependency_raises_di_error():
    container = Container()

    class NeedsMissing:
        def __init__(self, missing: IService) -> None:
            self.missing = missing

    container.register(NeedsMissing, NeedsMissing)
    with pytest.raises(DIError):
        container.resolve(NeedsMissing)


def test_unregistered_type_raises_di_error():
    container = Container()
    with pytest.raises(DIError):
        container.resolve(IService)


def test_invalid_lifetime_raises():
    container = Container()
    with pytest.raises(DIError):
        container.register(IService, Service, lifetime="bogus")


def test_generic_list_registration():
    container = Container()

    class Multi:
        def __init__(self, svcs: list[IService]) -> None:
            self.svcs = svcs

    container.register(IService, Service)
    container.register(list[IService], lambda: [Service("a"), Service("b")])
    container.register(Multi, Multi)

    multi = container.resolve(Multi)
    assert [s.run() for s in multi.svcs] == ["service-a", "service-b"]


def test_extra_kwargs_are_passed_to_constructor():
    container = Container()
    container.register(IService, Service, name="custom")
    assert container.resolve(IService).name == "custom"


@pytest.mark.asyncio
async def test_async_factory_resolution():
    container = Container()

    async def make_service() -> Service:
        return Service(name="async")

    container.register(IService, make_service)
    service = await container.resolve_async(IService)
    assert service.run() == "service-async"
