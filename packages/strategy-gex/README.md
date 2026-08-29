# GEX (Gamma Exposure) Strategy Plugin

Advanced options-based trading strategy using Gamma Exposure analysis for Power Trader.

## Overview

GEX (Gamma Exposure) measures the amount of gamma that options dealers have on their books. This creates natural support and resistance levels in the underlying asset.

## Strategy Logic

### What is GEX?

**Gamma Exposure** = Gamma × Open Interest × 100 × (Stock Price)²

- **Positive GEX (Dealer Long Gamma)**: Acts as support, reduces volatility
- **Negative GEX (Dealer Short Gamma)**: Acts as resistance, increases volatility

### Trading Signals

1. **BUY Signal**: Price approaches strong positive GEX level (support)
   - Dealers are long gamma → will buy as price falls → price support
   
2. **SELL Signal**: Price approaches strong negative GEX level (resistance)
   - Dealers are short gamma → will sell as price rises → price resistance

3. **HOLD Signal**: No nearby significant GEX levels

### Key Concepts

**Zero Gamma Level (Gamma Flip Point)**
- Strike where cumulative GEX changes from positive to negative
- Often acts as a pivot point for intraday price action

**Total Market GEX**
- Positive: Low volatility environment (range-bound)
- Negative: High volatility environment (trending)

## Installation

```bash
uv pip install -e packages/strategy-gex
```

## Features

- ✅ Black-Scholes gamma calculation
- ✅ GEX aggregation by strike price
- ✅ Key level identification
- ✅ Zero gamma (flip point) detection
- ✅ Support/resistance strength scoring
- ✅ Total market GEX analysis

## Configuration

```python
from power_trader_strategy_gex import GEXStrategy

strategy = GEXStrategy(
    lookback_days=30,           # Days of options data to analyze
    proximity_threshold=0.02,    # 2% - How close to GEX level for signal
    min_gex_strength=0.3,       # Minimum 30% relative strength
)
```

## Usage

Once installed, automatically discovered by power-day-trader:

```bash
power-day-trader monitor --symbols SPY --interval 60
```

## Understanding the Output

```python
{
    "current_price": 450.25,
    "total_gex": 1.5,  # Billions
    "gex_environment": "positive",  # Low volatility expected
    "zero_gamma_strike": 448.0,
    "signal_reason": "approaching_support",
    "support_strike": 445.0,
    "support_strength": 0.85,  # 85% strength
}
```

## Mathematical Background

### Gamma Calculation (Black-Scholes)

```
Gamma = N'(d1) / (S × σ × √T)

where:
d1 = [ln(S/K) + (r + σ²/2)T] / (σ√T)
N'(d1) = standard normal PDF
S = underlying price
K = strike price
σ = implied volatility
T = time to expiration (years)
r = risk-free rate
```

### GEX Convention

- **Calls**: Positive GEX (dealers long gamma)
- **Puts**: Negative GEX (dealers short gamma)

### Dealer Hedging Behavior

**When dealers are long gamma (positive GEX):**
- As stock price ↑ → dealers sell to hedge → creates resistance
- As stock price ↓ → dealers buy to hedge → creates support
- **Result**: Price compression (support)

**When dealers are short gamma (negative GEX):**
- As stock price ↑ → dealers buy to hedge → accelerates move
- As stock price ↓ → dealers sell to hedge → accelerates move
- **Result**: Price expansion (resistance)

## Production Integration

### Fetching Real Options Data

The strategy includes a placeholder for Interactive Brokers integration:

```python
async def _fetch_options_chain(self, symbol, current_price):
    # TODO: Implement IB API call
    # 1. Request options chain from IB
    # 2. Filter for liquid options
    # 3. Extract strike, OI, IV data
    # 4. Return list of OptionData
```

### Required Data Points

From Interactive Brokers API, fetch:
- Strike prices
- Expiration dates
- Option type (call/put)
- Open interest
- Implied volatility
- Underlying price

## Limitations

- Requires options chain data (not available for all symbols)
- More compute-intensive than simple technical strategies
- Best suited for high-liquidity underlyings (SPY, QQQ, AAPL, etc.)
- Mock data used in current implementation (requires IB integration)

## Advanced Usage

### Custom GEX Analysis

```python
from power_trader_strategy_gex.gex_calculator import GEXCalculator, OptionData

calculator = GEXCalculator(risk_free_rate=0.05)

# Calculate gamma for specific option
option = OptionData(...)
gamma = calculator.calculate_gamma(option)

# Calculate GEX
gex = calculator.calculate_gex(option)

# Aggregate by strike
gex_by_strike = calculator.aggregate_gex_by_strike(options)

# Find key levels
levels = calculator.identify_key_levels(gex_by_strike, current_price)

# Find zero gamma level
flip_point = calculator.find_zero_gamma_level(gex_by_strike)
```

## References

- **SpotGamma**: Pioneer in GEX analysis
- **Volatility Smile**: Options pricing and Greeks
- **Hull, J.C.**: "Options, Futures, and Other Derivatives"

## Testing

```bash
pytest packages/strategy-gex/ -v
```

## License

MIT
