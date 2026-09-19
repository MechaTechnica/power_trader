# Power Trader

A Python-based day trading system with ML strategy plugins and Interactive Brokers integration.

## 🏗️ Architecture

This is a monorepo containing multiple Python packages:

- **power-framework**: Core protocols and abstractions (no tech-specific code)
- **power-market**: Trading-domain contracts (market/signal types and protocols)
- **power-core**: Runtime infrastructure (application lifecycle, DI container, plugin registry)
- **power-day-trader**: Interactive Brokers application (hexagonal architecture)
- **power-trader-strategy-***: ML strategy plugins (momentum, GEX)

## 📋 Requirements

- Python 3.11+
- uv (package manager)
- Interactive Brokers TWS or IB Gateway

## 🚀 Quick Start

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all workspace packages
uv sync

# Run the trading app
uv run power-day-trader monitor --symbols AAPL MSFT
```

## 📦 Package Structure

```
power_trader/
├── packages/
│   ├── framework/           # power-framework → power_framework
│   ├── power-market/        # power-market → power_market
│   ├── power-core/          # power-core → power_core
│   ├── power-day-trader/    # power-day-trader → power_day_trader
│   ├── strategy-momentum/   # power-trader-strategy-momentum
│   └── strategy-gex/        # power-trader-strategy-gex
└── plans/
    └── architecture.md      # Detailed architecture documentation
```

Each package uses a three-layer naming convention: a short kebab-case directory
(e.g. `framework/`), a branded distribution name (e.g. `power-framework`), and a
snake_case import namespace (e.g. `power_framework`).

## 🛠️ Development

### Type Checking

```bash
mypy packages/
```

### Linting

```bash
ruff check packages/
ruff format packages/
```

### Testing

```bash
pytest
```

## 📖 Documentation

- [Architecture Plan](plans/architecture.md) - Comprehensive system design
- Getting Started Guide - Coming soon
- Creating Custom Strategies - Coming soon
- Interactive Brokers Setup - Coming soon

## 🎯 Key Features

- **Protocol-based architecture** - Clean separation of concerns
- **Automatic dependency injection** - Driven by type hints
- **Plugin system** - ML strategies as independent packages
- **Strict type checking** - Full mypy strict mode compliance
- **High performance** - Async I/O with dataclasses for hot paths
- **Hexagonal architecture** - Ports & adapters for the trading app

## 🔧 Technology Stack

- **Package Manager**: uv with workspace support
- **Type Checker**: mypy (strict mode)
- **Linter/Formatter**: ruff
- **Dependency Injection**: power-core `Container` (type-hint-driven)
- **Data Validation**: Pydantic (for config), dataclasses (for performance)
- **Testing**: pytest with pytest-asyncio
- **Market Data**: ib-insync (Interactive Brokers)

## 📝 License

MIT
