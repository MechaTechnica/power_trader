# Power Trader

A Python-based day trading system with ML strategy plugins and Interactive Brokers integration.

## 🏗️ Architecture

This is a monorepo containing multiple Python packages:

- **framework**: Core protocols and abstractions (no tech-specific code)
- **trading-app**: Interactive Brokers implementation
- **strategy-***: ML strategy plugins (momentum, volume profile, etc.)
- **cli-tools**: Scaffolding tools for creating apps and strategies

## 📋 Requirements

- Python 3.11+
- uv (package manager)
- Interactive Brokers TWS or IB Gateway

## 🚀 Quick Start

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Initialize workspace (after implementation)
uv sync

# Run the trading app
uv run power-trader-app --symbols AAPL MSFT

# Create a new strategy plugin
uv run power-trader create strategy my-strategy
```

## 📦 Package Structure

```
power_trader/
├── packages/
│   ├── framework/           # Core protocols and types
│   ├── trading-app/         # Main trading application
│   ├── strategy-*/          # Strategy plugins
│   └── cli-tools/           # CLI scaffolding tools
└── plans/
    └── architecture.md      # Detailed architecture documentation
```

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
- **Automatic dependency injection** - Using that-depends with type hints
- **Plugin system** - ML strategies as independent packages
- **Strict type checking** - Full mypy strict mode compliance
- **High performance** - Async I/O with dataclasses for hot paths
- **Extensible** - Ready for UI integration and custom strategies

## 🔧 Technology Stack

- **Package Manager**: uv with workspace support
- **Type Checker**: mypy (strict mode)
- **Linter/Formatter**: ruff
- **Dependency Injection**: that-depends
- **Data Validation**: Pydantic (for config), dataclasses (for performance)
- **Testing**: pytest with pytest-asyncio
- **Market Data**: ib-insync (Interactive Brokers)

## ⚠️ Status

**This project is currently in the planning/architecture phase.**

See [`plans/architecture.md`](plans/architecture.md) for the complete architectural design that will be implemented.

## 📝 License

MIT (to be added)
