"""Market data protocols."""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Protocol

from power_trader_framework.types.market import MarketBar, TickerSymbol, TimeInterval


class MarketDataProvider(Protocol):
    """
    Protocol for market data providers.
    
    This abstracts away the specific broker/data source (Interactive Brokers, etc.)
    Applications depend on this protocol, not concrete implementations.
    """

    async def connect(self) -> None:
        """
        Establish connection to data provider.
        
        Raises:
            ConnectionError: If connection fails
        """
        ...

    async def disconnect(self) -> None:
        """Close connection to data provider."""
        ...

    async def stream_bars(
        self,
        symbols: list[TickerSymbol],
        interval: TimeInterval,
    ) -> AsyncIterator[MarketBar]:
        """
        Stream real-time market bars for given symbols.
        
        Args:
            symbols: List of ticker symbols to stream
            interval: Time interval for bars
            
        Yields:
            MarketBar objects as they become available
            
        Raises:
            ConnectionError: If not connected
            ValueError: If symbols invalid
        """
        ...
        # Make mypy happy with async generator protocol
        if False:  # pragma: no cover
            yield MarketBar(
                symbol=symbols[0],
                timestamp=datetime.now(),
                open=0,
                high=0,
                low=0,
                close=0,
                volume=0,
            )

    async def get_historical_bars(
        self,
        symbol: TickerSymbol,
        interval: TimeInterval,
        start: datetime,
        end: datetime,
    ) -> list[MarketBar]:
        """
        Retrieve historical market bars.
        
        Args:
            symbol: Ticker symbol
            interval: Time interval for bars
            start: Start datetime (inclusive)
            end: End datetime (inclusive)
            
        Returns:
            List of historical bars
            
        Raises:
            ConnectionError: If not connected
            ValueError: If date range invalid
        """
        ...


class MarketScanner(Protocol):
    """
    Protocol for scanning/discovering tradeable securities.
    
    Used to find stocks matching criteria instead of manually specifying symbols.
    """

    async def scan_by_criteria(
        self,
        min_volume: int | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        sector: str | None = None,
        **kwargs: any,
    ) -> list[TickerSymbol]:
        """
        Scan market for stocks matching criteria.
        
        Args:
            min_volume: Minimum average volume
            min_price: Minimum stock price
            max_price: Maximum stock price
            sector: Sector/industry filter
            **kwargs: Additional provider-specific criteria
            
        Returns:
            List of ticker symbols matching criteria
            
        Raises:
            ConnectionError: If not connected
        """
        ...
