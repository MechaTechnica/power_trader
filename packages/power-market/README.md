# power-market

Trading-domain contracts for Power Trader applications. This package holds the
market and signal value types plus the protocol interfaces for market data,
scanning, strategies, and signal presentation.

It is deliberately **domain-specific** and separate from `power-framework`,
which contains only domain-agnostic application contracts (DI container,
lifecycle, plugin, config, and application bootstrap).

## Types

- **`TickerSymbol`** — instrument symbol (and optional exchange)
- **`MarketBar`** — OHLCV bar data (frozen dataclass with slots)
- **`TimeInterval`** — bar interval configuration
- **`TradingSignal`** — strategy signal output
- **`SignalMetadata`** — additional signal-generation context
- **`SignalType`** — signal enum (`BUY`/`SELL`/`HOLD`)

## Protocols

- **`MarketDataProvider`** — market data source (IB, Alpaca, etc.)
- **`MarketScanner`** — stock scanner/screener
- **`Strategy`** — ML trading strategy plugin
- **`SignalAggregator`** — multi-strategy signal combination
- **`SignalPresenter`** — trading-signal presentation

## Usage

```python
from power_market.types import MarketBar, TickerSymbol, TimeInterval
from power_market.protocols import MarketDataProvider, Strategy, SignalPresenter