"""Test support for applications built on the framework.

The framework's strongest selling point for internal teams is a *standard
testing story*. ``ApplicationTestHarness`` gives application teams a ready-made
test double stack so they can exercise their application end-to-end without
standing up real databases, brokers, or message buses.

The harness automatically substitutes the framework's defaults with in-memory,
*capturable* fakes:

- **captured events** — every event published to the (fake) event bus is recorded.
- **captured metrics** — an :class:`~power_framework.observability.InMemoryMetrics`
  whose counters/gauges/histograms can be asserted on.
- **captured spans** — an :class:`~power_framework.observability.InMemoryTracer`
  recording every traced operation.

For application-specific adapters (a database, a message bus, configuration), a
test supplies its own fake via :meth:`ApplicationTestHarness.replace`.

Usage::

    with ApplicationTestHarness(MyApplication) as app:
        await app.start()
        await app.publish(SomeDomainEvent(...))
        assert app.captured_events
        await app.stop()
"""

from __future__ import annotations

import asyncio
from typing import Any, Literal

from power_framework.application import (
    ApplicationBase,
    ApplicationBootstrapper,
    ApplicationBuilder,
    Runtime,
)
from power_framework.events import Event, EventBus, InMemoryEventBus
from power_framework.observability import InMemoryMetrics, InMemoryTracer, Metrics, Tracer


class RecordingEventBus(InMemoryEventBus):
    """An in-memory event bus that also records every published event."""

    def __init__(self, on_error: Any = None) -> None:
        super().__init__(on_error=on_error)
        self.published: list[Event] = []

    async def publish(self, event: Event) -> None:
        """Record ``event``, then fan it out to subscribers."""
        self.published.append(event)
        await super().publish(event)


class TestApplicationBuilder(ApplicationBuilder):
    """A builder for tests that can substitute fakes for real adapters.

    Usage::

        app = (
            TestApplicationBuilder(MyApplication)
            .replace(Database, FakeDatabase())
            .replace(MessageBus, InMemoryMessageBus())
            .build()
        )

    Replacements are applied *after* module wiring, so application teams can
    override any adapter without editing production wiring.
    """

    #: This is a production type, not a pytest test class, despite the name.
    __test__ = False

    def __init__(self, application_class: type[ApplicationBase]) -> None:
        super().__init__(application_class)
        self._overrides: list[tuple[Any, Any]] = []

    def replace(self, interface: Any, instance: Any) -> TestApplicationBuilder:
        """Substitute ``instance`` for ``interface`` when the application is built."""
        self._overrides.append((interface, instance))
        return self

    def validate(self) -> TestApplicationBuilder:
        """Validate the dependency graph including the registered overrides."""
        ApplicationBootstrapper().validate(
            self._application_class, overrides=self._overrides
        )
        return self

    def build(self) -> Runtime:
        """Build the application with the registered test overrides applied."""
        return ApplicationBootstrapper().bootstrap(
            self._application_class,
            validate=self._validate,
            overrides=self._overrides,
        )


class ApplicationTestHarness:
    """A context manager that builds an application with fakes substituted.

    On ``__enter__`` (or an explicit :meth:`build`) the harness assembles the
    application with the framework's event bus, metrics, and tracer replaced by
    capturing fakes. It returns itself, exposing ``start``/``stop``/``publish``
    helpers and the captured state.
    """

    def __init__(self, application_class: type[ApplicationBase]) -> None:
        self._application_class = application_class
        self._module_overrides: list[tuple[Any, Any]] = []

        self.metrics: InMemoryMetrics = InMemoryMetrics()
        self.tracer: InMemoryTracer = InMemoryTracer()
        self.event_bus: RecordingEventBus = RecordingEventBus()

        # Framework fakes are substituted *before* plugins wire, so plugins that
        # resolve the event bus/metrics/tracer during registration pick up these.
        self._framework_overrides: dict[Any, Any] = {
            EventBus: self.event_bus,
            Metrics: self.metrics,
            Tracer: self.tracer,
        }
        self._runtime: Runtime | None = None

    def replace(
        self, interface: Any, instance: Any
    ) -> ApplicationTestHarness:
        """Substitute ``instance`` for an application adapter (database, bus, ...)."""
        self._module_overrides.append((interface, instance))
        return self

    def build(self) -> ApplicationTestHarness:
        """Assemble the application with all fakes applied."""
        self._runtime = ApplicationBootstrapper().bootstrap(
            self._application_class,
            framework_overrides=self._framework_overrides,
            overrides=self._module_overrides,
        )
        return self

    # ------------------------------------------------------------------
    # Runtime access
    # ------------------------------------------------------------------
    @property
    def runtime(self) -> Runtime:
        if self._runtime is None:
            raise RuntimeError("The harness has not been built yet.")
        return self._runtime

    @property
    def application(self) -> ApplicationBase:
        """The resolved application instance."""
        return self.runtime.application

    async def start(self) -> None:
        """Start the runtime (components, then the application)."""
        await self.runtime.start()

    async def stop(self) -> None:
        """Stop the runtime (application, then components in reverse)."""
        await self.runtime.stop()

    async def publish(self, event: Event) -> None:
        """Publish ``event`` through the (fake) bus, recording it."""
        await self.event_bus.publish(event)

    @property
    def captured_events(self) -> list[Event]:
        """Every event published to the fake bus, in publication order."""
        return list(self.event_bus.published)

    @property
    def captured_spans(self) -> list[Any]:
        """Every span recorded by the fake tracer."""
        return list(self.tracer.spans)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------
    def __enter__(self) -> ApplicationTestHarness:
        self.build()
        return self

    def __exit__(self, *exc: object) -> Literal[False]:
        if self._runtime is not None:
            asyncio.run(self._runtime.stop())
        return False


__all__ = [
    "ApplicationTestHarness",
    "RecordingEventBus",
    "TestApplicationBuilder",
]
