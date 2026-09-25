"""Tests for dependency-graph validation and registration overrides."""

import pytest

from power_core.container import Container
from power_framework.exceptions import FrameworkError


class DatabaseConfiguration:
    """A leaf configuration dependency."""


class Database:
    def __init__(self, config: DatabaseConfiguration) -> None:
        self.config = config


class OrderRepository:
    def __init__(self, database: Database) -> None:
        self.database = database


class OrderService:
    def __init__(self, repository: OrderRepository) -> None:
        self.repository = repository


def _wired_container() -> Container:
    container = Container()
    container.register(DatabaseConfiguration, DatabaseConfiguration)
    container.register(Database, Database)
    container.register(OrderRepository, OrderRepository)
    container.register(OrderService, OrderService)
    return container


def test_validate_passes_when_dependency_graph_is_complete():
    container = _wired_container()
    # Should not raise.
    container.validate(OrderService)


def test_validate_raises_with_tree_on_missing_dependency():
    container = Container()
    container.register(Database, Database)  # Database -> DatabaseConfiguration (missing)
    container.register(OrderRepository, OrderRepository)
    container.register(OrderService, OrderService)

    with pytest.raises(FrameworkError) as exc_info:
        container.validate(OrderService)

    report = str(exc_info.value)
    assert "Application dependency validation failed" in report
    assert "OrderService" in report
    assert "OrderRepository" in report
    assert "Database" in report
    assert "DatabaseConfiguration" in report
    assert "✗ missing" in report


def test_validate_report_returns_formatted_tree_without_raising():
    container = Container()
    container.register(DatabaseConfiguration, DatabaseConfiguration)
    container.register(Database, Database)

    report = container.validate_report(Database)

    assert "Database" in report
    assert "DatabaseConfiguration" in report
    assert "✓" in report


def test_validate_defaults_to_all_registrations_when_no_roots():
    container = _wired_container()
    # No roots -> validate every registration; this graph is complete.
    container.validate()


def test_validate_marks_untyped_parameters_missing():
    class UntypedDependency:
        def __init__(self, database) -> None:
            self.database = database

    container = Container()
    container.register(UntypedDependency, UntypedDependency)

    with pytest.raises(FrameworkError) as exc_info:
        container.validate(UntypedDependency)

    assert "untyped" in str(exc_info.value)
    assert "✗ missing" in str(exc_info.value)


def test_override_replaces_an_existing_registration():
    container = Container()
    real = DatabaseConfiguration()
    container.register_instance(DatabaseConfiguration, real)

    fake = DatabaseConfiguration()
    container.override(DatabaseConfiguration, fake)

    assert container.resolve(DatabaseConfiguration) is fake


def test_override_registers_when_interface_was_absent():
    container = Container()
    fake = DatabaseConfiguration()
    container.override(DatabaseConfiguration, fake)

    assert container.resolve(DatabaseConfiguration) is fake
