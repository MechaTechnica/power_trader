# Implementation Guide

This document provides a step-by-step guide for implementing the Power Trader system based on the architecture defined in [`architecture.md`](architecture.md).

## Phase 1: Foundation Setup

### Step 1: Initialize Repository

```bash
# Initialize git repository
git init
git add .
git commit -m "Initial commit: Architecture documentation"

# Create .gitignore
```

**Files to create:**
- [`.gitignore`](../.gitignore)
- Root [`pyproject.toml`](../pyproject.toml) with workspace configuration

### Step 2: Configure Tooling

Create shared configuration files:

- [`mypy.ini`](../mypy.ini) - Strict type checking
- [`ruff.toml`](../ruff.toml) - Linting and formatting
- [`pytest.ini`](../pytest.ini) - Test configuration

### Step 3: Set Up Workspace

```bash
# Initialize uv workspace
uv init

# Create package directories
mkdir -p packages/{framework,trading-app,strategy-momentum,strategy-volume-profile,cli-tools}
```

## Phase 2: Framework Package

### Step 1: Create Package Structure

```bash
cd packages/framework
uv init --lib
```

Create the following structure:
```
framework/
├── pyproject.toml
├── README.md
├── src/power_framework/
│   ├── __init__.py
│   ├── protocols/
│   ├── core/
│   ├── types/
│   └── py.typed
└── tests/
```

### Step 2: Implement Types

**Priority order:**
1. [`types/common.py`](../packages/framework/src/power_framework/types/common.py) - Base enums and types
2. [`types/market.py`](../packages/framework/src/power_framework/types/market.py) - Market data types
3. [`types/signals.py`](../packages/framework/src/power_framework/types/signals.py) - Signal types

**Key considerations:**
- Use `@dataclass(frozen=True, slots=True)` for immutable types
- Use `Decimal` for price data
- Include validation in `__post_init__`

### Step 3: Implement Protocols

**Priority order:**
1. [`protocols/config.py`](../packages/framework/src/power_framework/protocols/config.py)
2. [`protocols/lifecycle.py`](../packages/framework/src/power_framework/protocols/lifecycle.py)
3. [`protocols/data.py`](../packages/framework/src/power_framework/protocols/data.py)
4. [`protocols/strategy.py`](../packages/framework/src/power_framework/protocols/strategy.py)
5. [`protocols/output.py`](../packages/framework/src/power_framework/protocols/output.py)

**Key considerations:**
- Use `Protocol` with runtime checkable where needed
- All methods should have clear type hints
- Include comprehensive docstrings

### Step 4: Implement Core Components

**Priority order:**
1. [`core/exceptions.py`](../packages/framework/src/power_framework/core/exceptions.py) - Custom exceptions
2. [`core/di_container.py`](../packages/framework/src/power_framework/core/di_container.py) - DI setup
3. [`core/plugin_loader.py`](../packages/framework/src/power_framework/core/plugin_loader.py) - Plugin discovery
4. [`core/application.py`](../packages/framework/src/power_framework/core/application.py) - App bootstrap

### Step 5: Write Framework Tests

**Test files:**
- `tests/test_types.py` - Test all type classes
- `tests/test_di_container.py` - Test DI resolution
- `tests/test_plugin_loader.py` - Test plugin discovery
- `tests/test_application.py` - Test lifecycle

**Target:** 90%+ code coverage

## Phase 3: Trading Application

### Step 1: Create Package Structure

```bash
cd packages/trading-app
uv init --app
```

### Step 2: Configuration Implementation

**Priority order:**
1. [`config/default.toml`](../packages/trading-app/src/power_trader_app/config/default.toml) - Default config
2. [`config/settings.py`](../packages/trading-app/src/power_trader_app/config/settings.py) - Pydantic settings

### Step 3: Interactive Brokers Integration

**Priority order:**
1. [`providers/ib_provider.py`](../packages/trading-app/src/power_trader_app/providers/ib_provider.py) - Data provider
2. [`providers/ib_scanner.py`](../packages/trading-app/src/power_trader_app/providers/ib_scanner.py) - Stock scanner

**Implementation notes:**
- Use `ib_insync` library
- Handle connection errors gracefully
- Implement reconnection logic
- Add logging for all API calls

### Step 4: Output Implementation

Implement [`output/terminal_output.py`](../packages/trading-app/src/power_trader_app/output/terminal_output.py):
- Use `rich` library for beautiful terminal output
- Format signals in a readable table
- Color-code buy/sell signals
- Show confidence scores as progress bars

### Step 5: Orchestration Layer

**Priority order:**
1. [`orchestration/signal_aggregator.py`](../packages/trading-app/src/power_trader_app/orchestration/signal_aggregator.py) - Combine signals
2. [`orchestration/trading_pipeline.py`](../packages/trading-app/src/power_trader_app/orchestration/trading_pipeline.py) - Main pipeline

### Step 6: CLI Interface

Implement [`cli.py`](../packages/trading-app/src/power_trader_app/cli.py):
- Use `click` or `typer` for CLI
- Support multiple input modes (manual tickers, scanner)
- Configuration file support
- Environment variable support

### Step 7: Main Entry Point

Implement [`main.py`](../packages/trading-app/src/power_trader_app/main.py):
- Set up DI container
- Register all implementations
- Initialize application
- Handle SIGINT/SIGTERM gracefully

## Phase 4: Strategy Plugins

### Step 1: Momentum Strategy

Create [`packages/strategy-momentum`](../packages/strategy-momentum):

**Implementation:**
- Calculate RSI (Relative Strength Index)
- Calculate MACD (Moving Average Convergence Divergence)
- Implement buy signal logic
- Add filters for:
  - Abnormal short interest detection
  - Unusual volume spike filtering

### Step 2: Volume Profile Strategy

Create [`packages/strategy-volume-profile`](../packages/strategy-volume-profile):

**Implementation:**
- Build volume profile from historical data
- Identify value areas and POC (Point of Control)
- Generate signals based on price action near key levels

### Step 3: Plugin Registration

Update each strategy's [`pyproject.toml`](../packages/strategy-momentum/pyproject.toml):

```toml
[project.entry-points."power_trader.strategies"]
momentum = "power_trader_strategy_momentum.strategy:MomentumStrategy"
```

## Phase 5: CLI Tools

### Step 1: Create Package Structure

Create [`packages/cli-tools`](../packages/cli-tools) with:
- Template system (Jinja2)
- Command handlers
- File generation logic

### Step 2: Implement Commands

**Commands to implement:**
1. `create app` - Generate new trading app
2. `create strategy` - Generate new strategy plugin
3. `templates list` - List available templates

### Step 3: Create Templates

**Templates needed:**
- App template with basic structure
- Strategy template with example strategy
- Test template for both

## Phase 6: Testing & Quality

### Step 1: Unit Tests

Write comprehensive unit tests for:
- All framework protocols (using mock implementations)
- All core framework components
- All trading app components
- Each strategy plugin

### Step 2: Integration Tests

Test:
- DI container with real implementations
- Strategy loading and execution
- Mock IB provider integration
- Signal aggregation with multiple strategies

### Step 3: End-to-End Tests

Test:
- Full pipeline with mock data
- Multiple symbols processing
- Error handling and recovery
- CLI commands

### Step 4: Type Checking

```bash
# Run mypy on all packages
mypy packages/framework
mypy packages/trading-app
mypy packages/strategy-momentum
mypy packages/strategy-volume-profile
mypy packages/cli-tools
```

**Target:** Zero mypy errors in strict mode

### Step 5: Code Quality

```bash
# Run ruff
ruff check packages/
ruff format packages/
```

**Target:** Zero ruff violations

## Phase 7: Documentation

### Step 1: Package READMEs

Write comprehensive READMEs for:
- [`packages/framework/README.md`](../packages/framework/README.md)
- [`packages/trading-app/README.md`](../packages/trading-app/README.md)
- Each strategy plugin

### Step 2: User Documentation

Create in [`docs/`](../docs):
- `getting_started.md` - Installation and first run
- `creating_strategies.md` - Strategy plugin development guide
- `ib_setup.md` - Interactive Brokers setup guide
- `configuration.md` - Configuration reference

### Step 3: API Documentation

Generate API docs using:
- Sphinx or MkDocs
- Include protocol documentation
- Include examples

## Phase 8: Deployment Preparation

### Step 1: Packaging

Ensure all packages:
- Have correct version numbers
- Have proper dependencies listed
- Include py.typed marker
- Have proper entry points

### Step 2: CI/CD Setup

Create GitHub Actions workflows for:
- Type checking (mypy)
- Linting (ruff)
- Testing (pytest)
- Coverage reporting

### Step 3: Release Preparation

- Create CHANGELOG.md
- Create LICENSE
- Create CONTRIBUTING.md
- Tag initial release

## Testing Checklist

Before considering implementation complete:

- [ ] All type hints pass mypy strict mode
- [ ] All code passes ruff checks
- [ ] Test coverage >90% for framework
- [ ] Test coverage >80% for trading-app
- [ ] Integration tests pass
- [ ] End-to-end tests pass
- [ ] CLI commands work as expected
- [ ] Can load and execute strategy plugins
- [ ] IB connection works (with real or paper trading account)
- [ ] Signals are correctly displayed in terminal
- [ ] All documentation is complete
- [ ] READMEs are clear and accurate

## Performance Considerations During Implementation

1. **Profile hot paths** - Use cProfile to identify bottlenecks
2. **Benchmark bar processing** - Ensure <10ms per bar
3. **Memory profiling** - Check for memory leaks in long-running processes
4. **Async efficiency** - Ensure proper use of asyncio

## Next Steps After Each Phase

After completing each phase:
1. Run all tests
2. Run type checker
3. Run linter
4. Update documentation
5. Commit changes
6. Review and refactor if needed

## Tips for Implementation

1. **Start simple** - Get the happy path working first
2. **Test early** - Write tests as you implement
3. **Type everything** - Don't skip type hints
4. **Use protocols** - Don't couple to implementations
5. **Log generously** - Add logging for debugging
6. **Handle errors** - Don't let exceptions crash the app
7. **Think async** - Use async/await throughout
8. **Validate inputs** - Check data at boundaries
9. **Document as you go** - Don't defer documentation
10. **Refactor often** - Keep code clean and simple

## Common Pitfalls to Avoid

1. ❌ Tight coupling between packages
2. ❌ Skipping type hints to save time
3. ❌ Not testing error paths
4. ❌ Blocking I/O in async functions
5. ❌ Over-engineering before needed
6. ❌ Not handling IB API errors
7. ❌ Ignoring performance until too late
8. ❌ Insufficient logging
9. ❌ Not using dependency injection properly
10. ❌ Mixing sync and async code incorrectly

## Estimated Implementation Order Duration

This is not a time estimate, but a complexity/priority ordering:

**Critical Path (MVP):**
1. Framework types and protocols
2. DI container setup
3. IB provider implementation
4. Basic pipeline
5. One strategy plugin
6. Terminal output
7. CLI

**Enhanced Features:**
8. Additional strategy plugins
9. Signal aggregation logic
10. CLI scaffolding tools
11. Advanced error handling
12. Configuration system

**Polish:**
13. Comprehensive testing
14. Documentation
15. CI/CD setup
