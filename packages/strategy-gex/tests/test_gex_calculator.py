"""Tests for GEX calculator."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from power_trader_strategy_gex.gex_calculator import GEXCalculator, OptionData


class TestGEXCalculator:
    """Tests for GEXCalculator."""

    def test_calculate_gamma_atm_call(self) -> None:
        """Test gamma calculation for ATM call option."""
        calculator = GEXCalculator()
        
        option = OptionData(
            strike=Decimal("100.0"),
            expiration=datetime.now() + timedelta(days=30),
            option_type="call",
            open_interest=1000,
            implied_volatility=0.25,
            underlying_price=Decimal("100.0"),  # ATM
        )
        
        gamma = calculator.calculate_gamma(option)
        
        # ATM options have highest gamma
        assert gamma > 0
        assert 0.01 < gamma < 0.1  # Reasonable range

    def test_calculate_gamma_otm_vs_itm(self) -> None:
        """Test that ATM has higher gamma than OTM/ITM."""
        calculator = GEXCalculator()
        
        expiration = datetime.now() + timedelta(days=30)
        underlying = Decimal("100.0")
        
        atm_option = OptionData(
            strike=Decimal("100.0"),
            expiration=expiration,
            option_type="call",
            open_interest=1000,
            implied_volatility=0.25,
            underlying_price=underlying,
        )
        
        otm_option = OptionData(
            strike=Decimal("110.0"),  # OTM
            expiration=expiration,
            option_type="call",
            open_interest=1000,
            implied_volatility=0.25,
            underlying_price=underlying,
        )
        
        atm_gamma = calculator.calculate_gamma(atm_option)
        otm_gamma = calculator.calculate_gamma(otm_option)
        
        # ATM should have higher gamma
        assert atm_gamma > otm_gamma

    def test_calculate_gex_call_positive(self) -> None:
        """Test that call options produce positive GEX."""
        calculator = GEXCalculator()
        
        call_option = OptionData(
            strike=Decimal("100.0"),
            expiration=datetime.now() + timedelta(days=30),
            option_type="call",
            open_interest=1000,
            implied_volatility=0.25,
            underlying_price=Decimal("100.0"),
        )
        
        gex = calculator.calculate_gex(call_option)
        
        # Calls should have positive GEX
        assert gex > 0

    def test_calculate_gex_put_negative(self) -> None:
        """Test that put options produce negative GEX."""
        calculator = GEXCalculator()
        
        put_option = OptionData(
            strike=Decimal("100.0"),
            expiration=datetime.now() + timedelta(days=30),
            option_type="put",
            open_interest=1000,
            implied_volatility=0.25,
            underlying_price=Decimal("100.0"),
        )
        
        gex = calculator.calculate_gex(put_option)
        
        # Puts should have negative GEX
        assert gex < 0

    def test_aggregate_gex_by_strike(self) -> None:
        """Test GEX aggregation by strike."""
        calculator = GEXCalculator()
        
        options = [
            OptionData(
                strike=Decimal("100.0"),
                expiration=datetime.now() + timedelta(days=30),
                option_type="call",
                open_interest=1000,
                implied_volatility=0.25,
                underlying_price=Decimal("100.0"),
            ),
            OptionData(
                strike=Decimal("100.0"),
                expiration=datetime.now() + timedelta(days=30),
                option_type="put",
                open_interest=800,
                implied_volatility=0.25,
                underlying_price=Decimal("100.0"),
            ),
        ]
        
        gex_by_strike = calculator.aggregate_gex_by_strike(options)
        
        assert Decimal("100.0") in gex_by_strike
        total_gex, call_gex, put_gex = gex_by_strike[Decimal("100.0")]
        
        # Verify structure
        assert call_gex > 0  # Calls positive
        assert put_gex < 0  # Puts negative
        assert abs(total_gex - (call_gex + put_gex)) < 1e-6  # Total is sum

    def test_identify_key_levels(self) -> None:
        """Test identification of key GEX levels."""
        calculator = GEXCalculator()
        
        # Create mock GEX data
        gex_by_strike = {
            Decimal("95.0"): (1000000.0, 1000000.0, 0.0),  # Support
            Decimal("100.0"): (-2000000.0, 500000.0, -2500000.0),  # Strong resistance
            Decimal("105.0"): (500000.0, 500000.0, 0.0),  # Weak support
        }
        
        levels = calculator.identify_key_levels(
            gex_by_strike, Decimal("100.0"), top_n=3
        )
        
        assert len(levels) == 3
        
        # Strongest should be first
        assert levels[0].strike == Decimal("100.0")
        assert levels[0].is_resistance  # Negative GEX
        assert levels[0].strength == 1.0  # Normalized to 1.0

    def test_calculate_total_gex(self) -> None:
        """Test total GEX calculation."""
        calculator = GEXCalculator()
        
        options = [
            OptionData(
                strike=Decimal("100.0"),
                expiration=datetime.now() + timedelta(days=30),
                option_type="call",
                open_interest=1000,
                implied_volatility=0.25,
                underlying_price=Decimal("100.0"),
            ),
            OptionData(
                strike=Decimal("100.0"),
                expiration=datetime.now() + timedelta(days=30),
                option_type="put",
                open_interest=500,
                implied_volatility=0.25,
                underlying_price=Decimal("100.0"),
            ),
        ]
        
        total_gex = calculator.calculate_total_gex(options)
        
        # Should have some net GEX
        assert total_gex != 0

    def test_find_zero_gamma_level(self) -> None:
        """Test finding zero gamma level."""
        calculator = GEXCalculator()
        
        # Create GEX data that crosses zero
        gex_by_strike = {
            Decimal("95.0"): (1000000.0, 1000000.0, 0.0),  # Positive
            Decimal("100.0"): (-500000.0, 200000.0, -700000.0),  # Negative - crosses here
            Decimal("105.0"): (-1000000.0, 0.0, -1000000.0),  # More negative
        }
        
        zero_level = calculator.find_zero_gamma_level(gex_by_strike)
        
        # Should find the crossing point
        assert zero_level == Decimal("100.0")

    def test_expired_option_zero_gamma(self) -> None:
        """Test that expired options have zero gamma."""
        calculator = GEXCalculator()
        
        expired_option = OptionData(
            strike=Decimal("100.0"),
            expiration=datetime.now() - timedelta(days=1),  # Expired
            option_type="call",
            open_interest=1000,
            implied_volatility=0.25,
            underlying_price=Decimal("100.0"),
        )
        
        gamma = calculator.calculate_gamma(expired_option)
        
        assert gamma == 0.0
