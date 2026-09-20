# Power Framework

**Pure protocols and types for building trading applications.**

## ⚠️ Important: NO IMPLEMENTATIONS

This package contains ONLY:
- ✅ Protocol definitions (interfaces)
- ✅ Type definitions (dataclasses)
- ❌ NO concrete implementations
- ❌ NO dependencies

Applications implement these protocols to create functioning systems.

## Overview

The Power Framework provides architecture-agnostic protocols and types. It defines **what** components should do, not **how** they do it. All implementations live in application packages like `power-day-trader`.

## Features

- **Type-Safe**: Strict type checking with mypy
- **Protocol-Based**: Pure interfaces with no implementation
- **Zero Dependencies**: Only standard library
- **Architecture-Agnostic**: Works with any architectural style
- **Performance-Optimized**: Dataclasses with slots for hot paths

## Installation

```bash
uv add power-framework
```

## What's Included

### Types

Immutable, type-safe data structures:

- **[`TickerSymbol`](src/power_framework/types/market.py)** - Stock symbol representation
- **[`MarketBar`](src/power_framework/types/market.py)** - OHLCV bar data (frozen dataclass with slots)
- **[`TimeInterval`](src/power_framework/types/market.py)** - Time interval configuration
- **[`TradingSignal`](src/power_framework/types/signals.py)** - Strategy signal output
- **[`SignalMetadata`](src/power_framework/types/signals.py)** - Additional signal information
- **[`SignalType`](src/power_framework/types/common.py)** - Signal enum (BUY/SELL/HOLD)

### Protocols

Interface definitions that applications implement:

#### Data Protocols
- **[`IMarketDataProvider`](src/power_framework/protocols/data.py)** - Market data source (IB, Alpaca, etc.)
- **[`IMarketScanner`](src/power_framework/protocols/data.py)** - Stock scanner/screener

#### Strategy Protocols
- **[`IStrategy`](src/power_framework/protocols/strategy.py)** - ML trading strategy plugin
- **[`ISignalAggregator`](src/power_framework/protocols/strategy.py)** - Multi-strategy signal combination

#### Output Protocols
- **[`IOutputPresenter`](src/power_framework/protocols/output.py)** - Result presentation (terminal, web, API)

#### System Protocols
- **[`IConfigProvider`](src/power_framework/protocols/config.py)** - Configuration management
- **[`IApplicationLifecycle`](src/power_framework/protocols/lifecycle.py)** - Startup/shutdown hooks
- **[`IHealthCheck`](src/power_framework/protocols/lifecycle.py)** - Health monitoring

## Usage Example

### Using Types

```python
from power_framework import MarketBar, TickerSymbol, TimeInterval
from decimal import Decimal
from datetime import datetime

# Create immutable types
symbol = TickerSymbol(symbol="AAPL", exchange="NASDAQ")
interval = TimeInterval.from_minutes(1)

bar = MarketBar(
    symbol=symbol,
    timestamp=datetime.now(),
    open=Decimal("150.00"),
    high=Decimal("151.00"),
    low=Decimal("149.50"),
    close=Decimal("150.50"),
    volume=1000000,
)
```

### Implementing Protocols

```python
from power_framework.protocols import IMarketDataProvider
from power_framework.types import MarketBar, TickerSymbol, TimeInterval
from collections.abc import AsyncIterator


class MyDataProvider:
    """Concrete implementation of IMarketDataProvider protocol."""

    async def connect(self) -> None:
        # Your implementation here
        pass

    async def disconnect(self) -> None:
        # Your implementation here
        pass

    async def stream_bars(
        self,
        symbols: list[TickerSymbol],
        interval: TimeInterval,
    ) -> AsyncIterator[MarketBar]:
        # Your implementation here
        while True:
            # yield bars...
            pass

    async def get_historical_bars(
        self,
        symbol: TickerSymbol,
        interval: TimeInterval,
        start: datetime,
        end: datetime,
    ) -> list[MarketBar]:
        # Your implementation here
        return []
```

### Implementing Strategy Plugins

```python
from power_framework.protocols import IStrategy
from power_framework.types import TradingSignal, SignalType, MarketBar
from datetime import datetime


class MomentumStrategy:
    """Concrete strategy implementation."""

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
            metadata={"rsi": 65.0},
        )

    async def initialize(self) -> None:
        # Load models, etc.
        pass

    async def cleanup(self) -> None:
        # Cleanup resources
        pass
```

## Design Philosophy

### Framework Responsibilities
✅ Define interfaces (protocols)  
✅ Define data structures (types)  
✅ Type safety and validation  

### Application Responsibilities
✅ Implement protocols  
✅ Business logic  
✅ Dependency injection setup  
✅ Application architecture (hexagonal, layered, etc.)  

## Architecture Support

The framework works with ANY architectural style:
- **Hexagonal Architecture** - Protocols as ports
- **Layered Architecture** - Protocols between layers
- **Event-Driven** - Protocols for event handlers
- **Clean Architecture** - Protocols for boundaries
- **Microservices** - Protocols for service contracts

## Example Applications

See complete implementations:
- **[power-day-trader](../power-day-trader)** - Day trading app with Interactive Brokers (Hexagonal Architecture)

## Type Checking

The framework is fully type-checked with mypy strict mode:

```bash
mypy --strict your_app.py
```

All protocols and types have complete type annotations.

## Performance

Types are optimized for performance:
- **Frozen dataclasses** - Immutable and hashable
- **Slots** - Memory efficient
- **Decimal** - Price precision without floating point errors

## License

MIT
