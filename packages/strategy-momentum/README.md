# Momentum Strategy Plugin

Simple momentum-based trading strategy for Power Trader.

## Strategy Logic

Calculates price momentum over configurable lookback period:
- **BUY** when momentum > 2% (strong uptrend)
- **SELL** when momentum < -2% (strong downtrend)
- **HOLD** otherwise

## Installation

```bash
uv pip install -e packages/strategy-momentum
```

The strategy will be automatically discovered via entry points.

## Configuration

The strategy is automatically loaded by power-day-trader when installed.

## Usage

Once installed, it's automatically used:

```bash
power-day-trader monitor --symbols AAPL
```

## Customization

Extend the `MomentumStrategy` class to customize:
- Lookback period
- Momentum thresholds
- Additional indicators (RSI, MACD, etc.)

## Example

```python
from power_trader_strategy_momentum import MomentumStrategy

# Custom lookback period
strategy = MomentumStrategy(lookback_periods=20)
```

## License

MIT
