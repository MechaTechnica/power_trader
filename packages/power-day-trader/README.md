# Power Day Trader

Day trading application using Interactive Brokers API with ML strategy plugins.

## Architecture

This application implements **Hexagonal Architecture (Ports & Adapters)** using the [`power-framework`](../framework/) protocols.

```
Core Domain (Inside Hexagon)
├── Use Cases: MonitorStocksUseCase
├── Depends on: Framework protocols only

Adapters (Outside Hexagon)
├── Primary (Driving): CLI
├── Secondary (Driven): IB Provider, Terminal Output, Signal Aggregator
```

## Features

- ✅ Interactive Brokers integration
- ✅ Real-time market data streaming
- ✅ Plugin-based ML strategies
- ✅ Signal aggregation from multiple strategies
- ✅ Rich terminal output
- ✅ Configurable via environment variables
- ✅ Hexagonal architecture for testability

## Installation

```bash
# From workspace root
uv sync

# Or install directly
cd packages/power-day-trader
uv pip install -e .
```

## Configuration

Configure via environment variables:

```bash
# Interactive Brokers
export IB_HOST=127.0.0.1
export IB_PORT=7497  # 7497=TWS paper, 4001=Gateway paper
export IB_CLIENT_ID=1

# Trading
export TRADING_DEFAULT_INTERVAL_SECONDS=60
export TRADING_MAX_CONCURRENT_SYMBOLS=10
```

## Usage

### Monitor Stocks

```bash
power-day-trader monitor --symbols AAPL MSFT GOOGL --interval 60
```

### With Custom Interval

```bash
# 30-second bars
power-day-trader monitor -s AAPL -i 30

# 5-minute bars
power-day-trader monitor -s TSLA -i 300
```

## Hexagonal Architecture

### Core/Domain (Inside Hexagon)

**[`core/use_cases/`](src/power_day_trader/core/use_cases/)**
- Pure business logic
- No knowledge of IB, CLI, terminal, etc.
- Only depends on framework protocols

### Primary Adapters (Driving)

**[`adapters/primary/`](src/power_day_trader/adapters/primary/)**
- [`cli_adapter.py`](src/power_day_trader/adapters/primary/cli_adapter.py) - Command-line interface
- Future: REST API, Web UI

### Secondary Adapters (Driven)

**[`adapters/secondary/`](src/power_day_trader/adapters/secondary/)**
- [`ib_provider.py`](src/power_day_trader/adapters/secondary/ib_provider.py) - Interactive Brokers data provider
- [`ib_scanner.py`](src/power_day_trader/adapters/secondary/ib_scanner.py) - Market scanner
- [`terminal_output.py`](src/power_day_trader/adapters/secondary/terminal_output.py) - Rich terminal output
- [`signal_aggregator.py`](src/power_day_trader/adapters/secondary/signal_aggregator.py) - Weighted average aggregation

### Configuration

**[`config/`](src/power_day_trader/config/)**
- [`settings.py`](src/power_day_trader/config/settings.py) - Pydantic settings with environment variable support

## Adding Strategy Plugins

Create a separate package implementing `IStrategy` protocol:

```python
from power_framework.protocols.strategy import IStrategy
from power_framework.types import TradingSignal, SignalType, MarketBar

class MyStrategy:
    @property
    def strategy_name(self) -> str:
        return "my-strategy-v1"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    async def analyze(self, bars: list[MarketBar]) -> TradingSignal:
        # Your logic here
        return TradingSignal(...)
    
    async def initialize(self) -> None:
        pass
    
    async def cleanup(self) -> None:
        pass
```

Register in `pyproject.toml`:

```toml
[project.entry-points."power_trader.strategies"]
my_strategy = "my_strategy_package:MyStrategy"
```

## Dependencies

### Runtime
- `power-framework` - Core protocols and types
- `that-depends` - Dependency injection
- `ib-insync` - Interactive Brokers API
- `pydantic` - Configuration validation
- `click` - CLI framework
- `rich` - Terminal formatting

### Development
- `mypy` - Type checking
- `ruff` - Linting/formatting
- `pytest` - Testing

## Interactive Brokers Setup

1. Install IB TWS or IB Gateway
2. Enable API connections in settings
3. Start TWS/Gateway
4. Run power-day-trader

**Paper Trading Ports:**
- TWS Paper: 7497
- Gateway Paper: 4001

**Live Trading Ports:**
- TWS Live: 7496
- Gateway Live: 4002

## Testing

```bash
# Run tests
pytest packages/power-day-trader

# With coverage
pytest --cov=power_day_trader packages/power-day-trader

# Type checking
mypy packages/power-day-trader/src
```

## Example Output

```
ℹ️  Starting monitoring of 3 symbols at 60s intervals

┌─── 📈 AAPL - BUY ────┐
│ Property   │ Value   │
│───────────────────────│
│ Confidence │ 85.0%   │
│ Strategy   │ momentum│
│ Time       │ 14:30:15│
│ Rsi        │ 65.0    │
└───────────────────────┘
```

## Architecture Benefits

**Testability**
- Mock all adapters to test use cases in isolation
- No need for real IB connection in tests

**Flexibility**
- Swap IB for another broker by changing adapter
- Add Web UI without touching business logic
- Change output format without touching core

**Future-Proof**
- Add features by adding new adapters
- Core business logic remains stable

## License

MIT
