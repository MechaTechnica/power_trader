# Copilot Instructions

## What this is

A Python monorepo for **Power Framework**: a reusable application foundation for
building banking/financial services. `power-day-trader` is the *example*
application that demonstrates how to use the framework; it is not the product.

## Package map

| Package | Purpose |
| --- | --- |
| `power_framework` | Protocols, settings, plugin discovery, lifecycle, observability. No runtime implementations. |
| `power_core` | Concrete runtime: DI container, bootstrap. |
| `power_market` | Trading-domain contracts (types + protocols). |
| `power_day_trader` | Example app (hexagonal: `adapters/`, `core/`, `config/`). |
| `power_trader_strategy_*` | Example strategy plugins. |

## Architecture rules

- **Protocols first.** Applications depend on `power_framework` protocols
  (`Container`, `Lifecycle`, `EventBus`, `Logger`), never on `power_core`
  concrete types.
- **DI by type hints.** Constructor arguments are auto-resolved. Never import the
  container inside a service or use case.
- **Plugins are composition units.** A `Plugin.register(container, runtime)`
  wires services and lifecycle components. Discovered via entry points.
- **Hexagonal.** `adapters/primary` = input, `adapters/secondary` = output,
  `core/use_cases` = business logic. Domain lives in `power_market`, not in apps.
- **Lifecycle is ordered.** Register start order in `runtime`; the runtime starts
  in order and stops in reverse.

## Conventions

- Python 3.11+, strict mypy, ruff (see `ruff.toml`). Run `uv run mypy`,
  `uv run ruff check`, `uv run pytest` before finishing.
- `from __future__ import annotations` everywhere.
- Docstrings are short. State *what/why*, not the obvious.
- Tests use `ApplicationTestHarness` to substitute fakes instead of real adapters.

## When changing code

- Adding a capability to the framework means adding a protocol, not a concrete
  class. Concrete implementations go into their domain specific project.
- Keep the example app (`power_day_trader`) small and readable — it is the
  onboarding guide.
- Prefer fakes (`InMemory*`, `ApplicationTestHarness`) over mocking frameworks.
