"""Test support for applications built on the framework.

The framework's strongest selling point for internal teams is a *standard
testing story*. ``ApplicationTestHarness`` gives application teams a ready-made
test double stack so they can exercise their application end-to-end without
standing up real databases, brokers, or message buses.

The harness automatically substitutes the framework's defaults with in-memory,
*capturable* fakes:

- **captured events** — every event published to the (fake) event bus is recorded.
- **captured metrics** — a :class:`RecordingMetrics` fake whose counters/gauges/
  histograms can be asserted on.
- **captured spans** — a :class:`RecordingTracer` fake recording every traced
  operation.

For application-specific adapters (a database, a message bus, configuration), a
test supplies its own fake via :meth:`ApplicationTestHarness.replace`.

Usage::

    with ApplicationTestHarness(MyApplication) as app:
        await app.start()
        await app.publish(SomeDomainEvent(...))
        assert app.captured_events
        await app.stop()
"""

import asyncio
import uuid
from collections import defaultdict
from typing import Any, Literal, Self

from power_framework.application import (ApplicationBase,
                                         ApplicationBootstrapper,
                                         ApplicationBuilder, Runtime)
from power_framework.events import Event, EventBus, EventHandler, HandlerSpec
from power_framework.observability import (Metrics, Span, Tracer,
                                           current_trace_id)


class RecordingEventBus:
    """An in-memory event bus (test fake) that records every published event.

    A minimal, self-contained ``EventBus`` owned by the framework's test
    harness. Unlike the production transports in ``power_core.events``, it only
    records published events and fans them out to matching subscribers — no
    retry, concurrency, or context stamping.
    """

    def __init__(self) -> None:
        self._subscribers: dict[type[Any], list[EventHandler]] = defaultdict(list)
        self.published: list[Event] = []

    def subscribe(self, event_type: type[Any], handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)

    def register(self, spec: HandlerSpec) -> None:
        self._subscribers[spec.event_type].append(spec.handler)

    async def publish(self, event: Event) -> None:
        """Record ``event``, then fan it out to matching subscribers."""
        self.published.append(event)
        for subscribed_type, handlers in self._subscribers.items():
            if issubclass(type(event), subscribed_type):
                for handler in handlers:
                    await handler.handle(event)


class RecordingMetrics:
    """A minimal in-memory ``Metrics`` fake that records values for assertions.

    A self-contained capture store owned by the framework's test harness (the
    production store lives in ``power_core.observability.InMemoryMetrics``).
    """

    def __init__(self) -> None:
        self._counters: dict[tuple[Any, ...], int] = defaultdict(int)
        self._gauges: dict[tuple[Any, ...], float] = {}
        self._histograms: dict[tuple[Any, ...], list[float]] = defaultdict(list)

    @staticmethod
    def _key(name: str, labels: dict[str, Any]) -> tuple[Any, ...]:
        return (name, *sorted(labels.items()))

    def increment(self, name: str, value: int = 1, **labels: Any) -> None:
        self._counters[self._key(name, labels)] += value

    def gauge(self, name: str, value: float, **labels: Any) -> None:
        self._gauges[self._key(name, labels)] = value

    def histogram(self, name: str, value: float, **labels: Any) -> None:
        self._histograms[self._key(name, labels)].append(value)

    def counter_value(self, name: str, **labels: Any) -> int:
        return self._counters[self._key(name, labels)]

    def gauge_value(self, name: str, **labels: Any) -> float:
        return self._gauges[self._key(name, labels)]

    def histogram_values(self, name: str, **labels: Any) -> list[float]:
        return list(self._histograms[self._key(name, labels)])


class RecordingTracer:
    """A minimal in-memory ``Tracer`` fake that records spans for assertions.

    A self-contained capture store owned by the framework's test harness (the
    production store lives in ``power_core.observability.InMemoryTracer``).
    """

    def __init__(self) -> None:
        self._spans: list[Span] = []

    def start_span(self, name: str, **attributes: Any) -> Span:
        span = Span(
            name=name,
            trace_id=current_trace_id() or str(uuid.uuid4()),
            attributes=dict(attributes),
        )
        self._spans.append(span)
        return span

    @property
    def spans(self) -> list[Span]:
        return list(self._spans)


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

    def replace(self, interface: Any, instance: Any) -> Self:
        """Substitute ``instance`` for ``interface`` when the application is built."""
        self._overrides.append((interface, instance))
        return self

    def validate(self) -> Self:
        """Validate the dependency graph including the registered overrides."""
        ApplicationBootstrapper().validate(self._application_class, overrides=self._overrides)
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

        self.metrics: RecordingMetrics = RecordingMetrics()
        self.tracer: RecordingTracer = RecordingTracer()
        self.event_bus: RecordingEventBus = RecordingEventBus()

        # Framework fakes are substituted *before* plugins wire, so plugins that
        # resolve the event bus/metrics/tracer during registration pick up these.
        self._framework_overrides: dict[Any, Any] = {
            EventBus: self.event_bus,
            Metrics: self.metrics,
            Tracer: self.tracer,
        }
        self._runtime: Runtime | None = None

    def replace(self, interface: Any, instance: Any) -> Self:
        """Substitute ``instance`` for an application adapter (database, bus, ...)."""
        self._module_overrides.append((interface, instance))
        return self

    def build(self) -> Self:
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
    def __enter__(self) -> Self:
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
