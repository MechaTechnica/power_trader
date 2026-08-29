"""GEX (Gamma Exposure) calculation module."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import numpy as np
from scipy.stats import norm


@dataclass
class OptionData:
    """Option contract data."""

    strike: Decimal
    expiration: datetime
    option_type: str  # 'call' or 'put'
    open_interest: int
    implied_volatility: float
    underlying_price: Decimal


@dataclass
class GEXLevel:
    """GEX level with support/resistance information."""

    strike: Decimal
    total_gamma: float
    call_gamma: float
    put_gamma: float
    is_resistance: bool  # True if negative gamma (dealer short)
    strength: float  # 0.0 to 1.0


class GEXCalculator:
    """
    Calculate Gamma Exposure (GEX) from options chain data.
    
    GEX represents the amount of gamma dealers have on their books.
    - Positive GEX (dealer long gamma): Acts as support, reduces volatility
    - Negative GEX (dealer short gamma): Acts as resistance, increases volatility
    """

    def __init__(self, risk_free_rate: float = 0.05) -> None:
        """
        Initialize GEX calculator.
        
        Args:
            risk_free_rate: Annual risk-free interest rate (default 5%)
        """
        self.risk_free_rate = risk_free_rate

    def calculate_gamma(self, option: OptionData) -> float:
        """
        Calculate gamma for a single option using Black-Scholes.
        
        Gamma = N'(d1) / (S * σ * sqrt(T))
        
        Where:
        - N'(d1) is the standard normal PDF
        - S is the underlying price
        - σ is implied volatility
        - T is time to expiration in years
        
        Args:
            option: Option contract data
            
        Returns:
            Gamma value (change in delta per $1 move in underlying)
        """
        S = float(option.underlying_price)
        K = float(option.strike)
        T = self._time_to_expiration(option.expiration)
        sigma = option.implied_volatility
        r = self.risk_free_rate

        if T <= 0 or sigma <= 0:
            return 0.0

        # Calculate d1
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))

        # Calculate gamma
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))

        return gamma

    def calculate_gex(self, option: OptionData) -> float:
        """
        Calculate gamma exposure for a single option.
        
        GEX = Gamma * Open Interest * 100 * S²
        
        Convention:
        - Calls: Positive GEX (dealers are long gamma)
        - Puts: Negative GEX (dealers are short gamma)
        
        Args:
            option: Option contract data
            
        Returns:
            Gamma exposure in dollars
        """
        gamma = self.calculate_gamma(option)
        S = float(option.underlying_price)

        # Each option controls 100 shares
        gex = gamma * option.open_interest * 100 * (S**2)

        # Convention: calls positive, puts negative
        if option.option_type.lower() == "put":
            gex = -gex

        return gex

    def aggregate_gex_by_strike(
        self, options: list[OptionData]
    ) -> dict[Decimal, tuple[float, float, float]]:
        """
        Aggregate GEX by strike price.
        
        Args:
            options: List of option contracts
            
        Returns:
            Dictionary mapping strike -> (total_gex, call_gex, put_gex)
        """
        gex_by_strike: dict[Decimal, list[float]] = {}

        for option in options:
            gex = self.calculate_gex(option)

            if option.strike not in gex_by_strike:
                gex_by_strike[option.strike] = [0.0, 0.0, 0.0]  # total, calls, puts

            gex_by_strike[option.strike][0] += gex

            if option.option_type.lower() == "call":
                gex_by_strike[option.strike][1] += gex
            else:
                gex_by_strike[option.strike][2] += gex

        return {k: (v[0], v[1], v[2]) for k, v in gex_by_strike.items()}

    def identify_key_levels(
        self,
        gex_by_strike: dict[Decimal, tuple[float, float, float]],
        current_price: Decimal,
        top_n: int = 5,
    ) -> list[GEXLevel]:
        """
        Identify key GEX support/resistance levels.
        
        Args:
            gex_by_strike: GEX aggregated by strike
            current_price: Current underlying price
            top_n: Number of top levels to return
            
        Returns:
            List of key GEX levels sorted by absolute strength
        """
        levels = []

        for strike, (total_gex, call_gex, put_gex) in gex_by_strike.items():
            # Skip zero GEX strikes
            if abs(total_gex) < 1e-6:
                continue

            # Determine if resistance (negative GEX) or support (positive GEX)
            is_resistance = total_gex < 0

            levels.append(
                GEXLevel(
                    strike=strike,
                    total_gamma=total_gex,
                    call_gamma=call_gex,
                    put_gamma=put_gex,
                    is_resistance=is_resistance,
                    strength=abs(total_gex),
                )
            )

        # Sort by strength and take top N
        levels.sort(key=lambda x: x.strength, reverse=True)

        # Normalize strength to 0-1 range
        if levels:
            max_strength = levels[0].strength
            for level in levels:
                level.strength = level.strength / max_strength if max_strength > 0 else 0.0

        return levels[:top_n]

    def calculate_total_gex(self, options: list[OptionData]) -> float:
        """
        Calculate total market GEX.
        
        Positive total GEX: Low volatility environment (dealer long gamma)
        Negative total GEX: High volatility environment (dealer short gamma)
        
        Args:
            options: List of option contracts
            
        Returns:
            Total GEX across all strikes
        """
        return sum(self.calculate_gex(option) for option in options)

    def find_zero_gamma_level(
        self, gex_by_strike: dict[Decimal, tuple[float, float, float]]
    ) -> Decimal | None:
        """
        Find the strike where cumulative GEX changes from positive to negative.
        
        This is often called the "gamma flip point" and represents a key level.
        
        Args:
            gex_by_strike: GEX aggregated by strike
            
        Returns:
            Strike price of zero gamma level, or None if not found
        """
        strikes_sorted = sorted(gex_by_strike.keys())

        cumulative_gex = 0.0
        prev_strike = None
        prev_cumulative = None

        for strike in strikes_sorted:
            total_gex = gex_by_strike[strike][0]
            cumulative_gex += total_gex

            # Check if we crossed zero
            if prev_cumulative is not None:
                if (prev_cumulative > 0 and cumulative_gex < 0) or (
                    prev_cumulative < 0 and cumulative_gex > 0
                ):
                    # Return the strike where crossing occurred
                    return strike

            prev_strike = strike
            prev_cumulative = cumulative_gex

        return None

    @staticmethod
    def _time_to_expiration(expiration: datetime) -> float:
        """
        Calculate time to expiration in years.
        
        Args:
            expiration: Expiration datetime
            
        Returns:
            Time to expiration in years
        """
        now = datetime.now()
        time_diff = expiration - now
        return max(time_diff.total_seconds() / (365.25 * 24 * 3600), 0.0)
