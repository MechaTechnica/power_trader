"""Trading-signal presentation protocol."""

from typing import Protocol

from power_market.types.market import TickerSymbol
from power_market.types.signals import Signal, SignalMetadata


class SignalPresenter(Protocol):
    """
    Protocol for presenting trading signals to the user.

    This is the *domain-specific* presentation concern. Generic status,
    warning, and error reporting live in
    ``power_framework.protocols.output.OutputPresenter``; concrete adapters may
    implement both protocols.
    """

    async def present_signal(
        self,
        symbol: TickerSymbol,
        signal: Signal,
        metadata: SignalMetadata,
    ) -> None:
        """
        Present a trading signal to the user.

        Args:
            symbol: Stock symbol
            signal: Trading signal from a strategy
            metadata: Additional context about signal generation
        """
        ...
