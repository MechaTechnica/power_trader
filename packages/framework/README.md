# Power Trader Framework

Core protocols and abstractions for building trading applications.

## Overview

The Power Trader Framework provides architecture-agnostic protocols and types that enable you to build trading applications with clean separation of concerns. The framework enforces no specific architectural style - use hexagonal, layered, event-driven, or any other architecture you prefer.

## Features

- **Type-Safe**: Strict type checking with mypy
- **Protocol-Based**: Depend on interfaces, not implementations
- **Dependency Injection**: Automatic constructor injection with that-depends
- **Plugin System**: Dynamic strategy loading via entry points
- **Performance-Optimized**: Dataclasses with slots for hot paths
- **Architecture-Agnostic**: Works with any architectural style

## Installation

```bash
uv add power-trader-framework
```

## Core Concepts

### Types

Immutable, type-safe data structures:

- `TickerSymbol` - Stock symbol representation
- `MarketBar` - OHLCV bar data
- `TimeInterval` - Time interval configuration
- `TradingSignal` - Strategy signal output
- `SignalMetadata` - Additional signal information

### Protocols

Interface definitions for pluggable components:

- `IMarketDataProvider` - Market data source (IB, Alpaca, etc.)
- `IStrategy` - ML trading strategy
- `ISignalAggregator` - Multi-strategy signal combination
- `IOutputPresenter` - Result presentation (terminal, web, API)
- `IConfigProvider` - Configuration management
- `IApplicationLifecycle` - Startup/shutdown hooks

### Core Components

- `DIContainer` - Dependency injection container
- `PluginRegistry` - Strategy plugin discovery and loading
- `Application` - Application lifecycle management

## Usage

### Creating a Trading Application

```python
from power_trader_framework import MarketBar, TickerSymbol, TimeInterval
from power_trader_framework.protocols import IMarketDataProvider, IStrategy
from power_trader_framework.core import Application, DIContainer

# Implement protocols
class MyDataProvider:
    async def connect(self) -> None:
        # Connect to broker
        pass
    
    async def stream_bars(self, symbols, interval):
        # Stream market data
        pass

# Set up DI container
class MyContainer(DIContainer):
    data_provider = providers.Singleton(MyDataProvider)
    # ... register other dependencies

# Bootstrap application
container = MyContainer()
app = Application(container)

# Register lifecycle hooks
app.on_startup(container.data_provider().connect)
app.on_shutdown(container.data_provider().disconnect)

# Run
await app.run()
```

### Creating a Strategy Plugin

```python
from power_trader_framework import TradingSignal, SignalType
from power_trader_framework.types.market import MarketBar

class MomentumStrategy:
    """Strategy plugin implementing IStrategy protocol."""
    
    @property
    def strategy_name(self) -> str:
        return "momentum-v1"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    async def analyze(self, bars: list[MarketBar]) -> TradingSignal:
        # Your strategy logic here
        return TradingSignal(
            signal_type=SignalType.BUY,
            confidence=0.85,
            timestamp=datetime.now(),
            strategy_name=self.strategy_name,
            metadata={"rsi": 65}
        )
    
    async def initialize(self) -> None:
        # Load models, warm cache, etc.
        pass
    
    async def cleanup(self) -> None:
        # Cleanup resources
        pass
```

Register in `pyproject.toml`:

```toml
[project.entry-points."power_trader.strategies"]
momentum = "my_strategy_package:MomentumStrategy"
```

## Architecture Support

The framework works with any architectural style:

- **Hexagonal Architecture** - Use protocols as ports
- **Layered Architecture** - Use protocols between layers
- **Event-Driven Architecture** - Use protocols for event handlers
- **Clean Architecture** - Use protocols for boundaries
- **Microservices** - Use protocols for service interfaces

## Testing

All components are designed for easy testing:

```python
# Mock any protocol for testing
class MockDataProvider:
    async def stream_bars(self, symbols, interval):
        # Return test data
        yield test_bar

# Test business logic in isolation
strategy = MyStrategy()
signal = await strategy.analyze(test_bars)
assert signal.signal_type == SignalType.BUY
```

## Performance

The framework is optimized for performance:

- **Dataclasses with slots** for memory efficiency
- **Frozen dataclasses** for immutability and hashability
- **Decimal types** for price precision
- **Async/await** throughout for I/O efficiency
- **Minimal abstractions** in hot paths

## Type Checking

The framework is fully type-checked with mypy strict mode:

```bash
mypy --strict your_app.py
```

All public APIs have complete type annotations.

## Examples

See the [`trading-app`](../trading-app) package for a complete example using Interactive Brokers.

## License

MIT
