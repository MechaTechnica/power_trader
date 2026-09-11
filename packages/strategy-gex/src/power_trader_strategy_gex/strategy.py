"""GEX trading strategy implementation."""

from datetime import datetime
from decimal import Decimal

from power_trader_framework.protocols.strategy import IStrategy
from power_trader_framework.types.common import SignalType
from power_trader_framework.types.market import MarketBar
from power_trader_framework.types.signals import TradingSignal
from power_trader_strategy_gex.gex_calculator import (GEXCalculator, GEXLevel,
                                                      OptionData)


class GEXStrategy:
    """
    GEX (Gamma Exposure) trading strategy.
    
    Strategy logic:
    1. Calculate GEX levels from options chain
    2. Identify key support (positive GEX) and resistance (negative GEX) levels
    3. Generate signals based on price action relative to GEX levels
    
    Signal rules:
    - BUY when price approaches strong positive  GEX level (support)
    - SELL when price approaches strong negative GEX level (resistance)
    - HOLD otherwise or in low GEX environment
    
    Implements IStrategy protocol as a plugin.
    """

    def __init__(
        self,
        calculator: GEXCalculator,
        lookback_days: int = 30,
        proximity_threshold: float = 0.02,  # 2% from GEX level
        min_gex_strength: float = 0.3,  # Minimum 30% strength to consider
    ) -> None:
        """
        Initialize GEX strategy.

        Args:
            calculator: Injected GEX calculator service.
            lookback_days: Days to look back for options data
            proximity_threshold: Price must be within this % of GEX level
            min_gex_strength: Minimum normalized strength (0-1) to consider a level
        """
        self.lookback_days = lookback_days
        self.proximity_threshold = proximity_threshold
        self.min_gex_strength = min_gex_strength
        self.gex_calculator = calculator

        # Cache for options data (would be fetched from IB in production)
        self._options_cache: list[OptionData] = []

    @property
    def strategy_name(self) -> str:
        """Strategy identifier."""
        return "gex-v1"

    @property
    def version(self) -> str:
        """Strategy version."""
        return "0.1.0"

    async def analyze(self, bars: list[MarketBar]) -> TradingSignal:
        """
        Analyze market using GEX levels.
        
        Args:
            bars: Historical market bars (oldest to newest)
            
        Returns:
            TradingSignal with recommendation
        """
        if not bars:
            return self._create_signal(
                SignalType.HOLD, 0.5, {"reason": "no_data"}
            )

        current_bar = bars[-1]
        current_price = float(current_bar.close)

        # Fetch options chain (in production, this would call IB API)
        # For now, using cached/mock data
        options = await self._fetch_options_chain(current_bar.symbol, current_price)

        if not options:
            return self._create_signal(
                SignalType.HOLD,
                0.5,
                {
                    "reason": "no_options_data",
                    "current_price": current_price,
                },
            )

        # Calculate GEX by strike
        gex_by_strike = self.gex_calculator.aggregate_gex_by_strike(options)

        # Identify key GEX levels
        key_levels = self.gex_calculator.identify_key_levels(
            gex_by_strike, current_bar.close, top_n=5
        )

        # Calculate total market GEX
        total_gex = self.gex_calculator.calculate_total_gex(options)

        # Find zero gamma level
        zero_gamma_strike = self.gex_calculator.find_zero_gamma_level(gex_by_strike)

        # Generate signal based on GEX analysis
        signal_type, confidence, metadata = self._generate_signal(
            current_price, key_levels, total_gex, zero_gamma_strike
        )

        return self._create_signal(signal_type, confidence, metadata)

    def _generate_signal(
        self,
        current_price: float,
        key_levels: list[GEXLevel],
        total_gex: float,
        zero_gamma_strike: Decimal | None,
    ) -> tuple[SignalType, float, dict]:
        """
        Generate trading signal from GEX analysis.
        
        Args:
            current_price: Current stock price
            key_levels: Key GEX support/resistance levels
            total_gex: Total market GEX
            zero_gamma_strike: Zero gamma flip point
            
        Returns:
            Tuple of (signal_type, confidence, metadata)
        """
        metadata = {
            "current_price": round(current_price, 2),
            "total_gex": round(total_gex / 1e9, 2),  # In billions
            "gex_environment": "positive" if total_gex > 0 else "negative",
            "zero_gamma_strike": float(zero_gamma_strike) if zero_gamma_strike else None,
            "key_levels": [],
        }

        # No strong levels found
        if not key_levels:
            return SignalType.HOLD, 0.5, {**metadata, "reason": "no_key_levels"}

        # Find nearby levels
        nearby_levels = [
            level
            for level in key_levels
            if abs(float(level.strike) - current_price) / current_price
            <= self.proximity_threshold
            and level.strength >= self.min_gex_strength
        ]

        # Add top 3 levels to metadata
        for i, level in enumerate(key_levels[:3]):
            metadata["key_levels"].append(
                {
                    f"level_{i+1}_strike": float(level.strike),
                    f"level_{i+1}_type": "resistance" if level.is_resistance else "support",
                    f"level_{i+1}_strength": round(level.strength, 2),
                }
            )

        if not nearby_levels:
            return SignalType.HOLD, 0.6, {**metadata, "reason": "no_nearby_levels"}

        # Prioritize strongest nearby level
        strongest_level = max(nearby_levels, key=lambda x: x.strength)

        # BUY signal: Approaching strong support (positive GEX)
        if not strongest_level.is_resistance:
            confidence = 0.5 + (strongest_level.strength * 0.4)  # 0.5 to 0.9
            return (
                SignalType.BUY,
                confidence,
                {
                    **metadata,
                    "signal_reason": "approaching_support",
                    "support_strike": float(strongest_level.strike),
                    "support_strength": round(strongest_level.strength, 2),
                },
            )

        # SELL signal: Approaching strong resistance (negative GEX)
        else:
            confidence = 0.5 + (strongest_level.strength * 0.4)  # 0.5 to 0.9
            return (
                SignalType.SELL,
                confidence,
                {
                    **metadata,
                    "signal_reason": "approaching_resistance",
                    "resistance_strike": float(strongest_level.strike),
                    "resistance_strength": round(strongest_level.strength, 2),
                },
            )

    async def _fetch_options_chain(
        self, symbol: any, current_price: float
    ) -> list[OptionData]:
        """
        Fetch options chain data.
        
        In production, this would:
        1. Connect to Interactive Brokers API
        2. Fetch options chain for the symbol
        3. Filter for liquid options (volume > threshold)
        4. Return list of OptionData
        
        For now, returns mock data for demonstration.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            
        Returns:
            List of option contracts
        """
        # TODO: Implement actual IB API call
        # For demonstration, return mock data
        
        if self._options_cache:
            return self._options_cache
        
        # Mock options chain (in production, fetch from IB)
        # Create ATM and nearby strikes
        mock_options = []
        base_price = Decimal(str(int(current_price)))
        
        # Create options at multiple strikes around current price
        for offset in range(-10, 11):
            strike = base_price + Decimal(offset * 5)
            
            # Mock call option
            mock_options.append(
                OptionData(
                    strike=strike,
                    expiration=datetime(2024, 12, 20),  # Mock expiration
                    option_type="call",
                    open_interest=1000 + abs(offset) * 100,
                    implied_volatility=0.25 + abs(offset) * 0.01,
                    underlying_price=Decimal(str(current_price)),
                )
            )
            
            # Mock put option
            mock_options.append(
                OptionData(
                    strike=strike,
                    expiration=datetime(2024, 12, 20),
                    option_type="put",
                    open_interest=800 + abs(offset) * 120,
                    implied_volatility=0.28 + abs(offset) * 0.01,
                    underlying_price=Decimal(str(current_price)),
                )
            )
        
        self._options_cache = mock_options
        return mock_options

    async def initialize(self) -> None:
        """Initialize strategy (called once on startup)."""
        # Could pre-load options data, warm up caches, etc.
        pass

    async def cleanup(self) -> None:
        """Cleanup strategy resources (called on shutdown)."""
        self._options_cache.clear()

    def _create_signal(
        self, signal_type: SignalType, confidence: float, metadata: dict
    ) -> TradingSignal:
        """Helper to create trading signal."""
        return TradingSignal(
            signal_type=signal_type,
            confidence=confidence,
            timestamp=datetime.now(),
            strategy_name=self.strategy_name,
            metadata=metadata,
        )
