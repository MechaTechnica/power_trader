"""Output/presentation protocols."""

from typing import Protocol

from power_trader_framework.types.market import TickerSymbol
from power_trader_framework.types.signals import SignalMetadata, TradingSignal


class IOutputPresenter(Protocol):
    """
    Protocol for presenting trading signals.
    
    This abstracts the output mechanism:
    - Terminal/CLI (current)
    - Web UI (future)
    - REST API (future)
    - File/log (future)
    - Alert system (future)
    """

    async def present_signal(
        self,
        symbol: TickerSymbol,
        signal: TradingSignal,
        metadata: SignalMetadata,
    ) -> None:
        """
        Present a trading signal to the user.
        
        Args:
            symbol: Stock symbol
            signal: Trading signal from strategy
            metadata: Additional context about signal generation
        """
        ...

    async def present_error(self, error: Exception) -> None:
        """
        Present an error to the user.
        
        Args:
            error: Exception that occurred
        """
        ...

    async def present_status(self, message: str) -> None:
        """
        Present a status message to the user.
        
        Args:
            message: Status message (e.g., "Connected to broker")
        """
        ...

    async def present_warning(self, message: str) -> None:
        """
        Present a warning message to the user.
        
        Args:
            message: Warning message
        """
        ...
