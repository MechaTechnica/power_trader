"""Interactive Brokers data provider adapter."""

from collections.abc import AsyncIterator
from datetime import datetime
from decimal import Decimal

from ib_insync import IB, Stock, util
from power_market.protocols.data import MarketDataProvider
from power_market.types.market import MarketBar, TickerSymbol, TimeInterval


class InteractiveBrokersAdapter:
    """
    Interactive Brokers adapter implementing MarketDataProvider.
    
    Uses ib_insync library to communicate with IB TWS/Gateway.
    """

    def __init__(self, host: str, port: int, client_id: int) -> None:
        """
        Initialize IB adapter.
        
        Args:
            host: IB Gateway/TWS host (usually '127.0.0.1')
            port: IB Gateway/TWS port (7497 for TWS paper, 4001 for Gateway paper)
            client_id: Client ID for this connection
        """
        self._ib = IB()
        self._host = host
        self._port = port
        self._client_id = client_id
        self._connected = False

    async def start(self) -> None:
        """Establish connection to Interactive Brokers."""
        if self._connected:
            return
        
        await self._ib.connectAsync(self._host, self._port, self._client_id)
        self._connected = True

    async def stop(self) -> None:
        """Close connection to Interactive Brokers."""
        if self._connected:
            self._ib.disconnect()
            self._connected = False

    async def stream_bars(
        self,
        symbols: list[TickerSymbol],
        interval: TimeInterval,
    ) -> AsyncIterator[MarketBar]:
        """
        Stream real-time bars from Interactive Brokers.
        
        Note: IB has specific bar size limitations.
        Real-time bars are available in 5-second increments.
        """
        if not self._connected:
            raise ConnectionError("Not connected to Interactive Brokers")
        
        # Map our interval to IB bar size
        bar_size_str = self._map_interval_to_ib_bar_size(interval)
        
        for symbol in symbols:
            # Create IB contract
            contract = Stock(symbol.symbol, "SMART", "USD")
            self._ib.qualifyContracts(contract)
            
            # Subscribe to real-time bars
            bars = self._ib.reqRealTimeBars(
                contract,
                barSize=5,  # IB only supports 5-second bars for real-time
                whatToShow="TRADES",
                useRTH=False,  # Include extended hours
            )
            
            # Yield bars as they come in
            async for ib_bar in bars:
                yield self._convert_ib_bar_to_market_bar(symbol, ib_bar)

    async def get_historical_bars(
        self,
        symbol: TickerSymbol,
        interval: TimeInterval,
        start: datetime,
        end: datetime,
    ) -> list[MarketBar]:
        """Retrieve historical bars from Interactive Brokers."""
        if not self._connected:
            raise ConnectionError("Not connected to Interactive Brokers")
        
        # Create IB contract
        contract = Stock(symbol.symbol, "SMART", "USD")
        self._ib.qualifyContracts(contract)
        
        # Calculate duration
        duration_str = self._calculate_duration(start, end)
        bar_size_str = self._map_interval_to_ib_bar_size(interval)
        
        # Request historical data
        ib_bars = self._ib.reqHistoricalData(
            contract,
            endDateTime=end,
            durationStr=duration_str,
            barSizeSetting=bar_size_str,
            whatToShow="TRADES",
            useRTH=False,
            formatDate=1,
        )
        
        # Convert to our MarketBar format
        return [self._convert_ib_bar_to_market_bar(symbol, bar) for bar in ib_bars]

    def _convert_ib_bar_to_market_bar(self, symbol: TickerSymbol, ib_bar: any) -> MarketBar:
        """Convert IB bar to our MarketBar format."""
        return MarketBar(
            symbol=symbol,
            timestamp=ib_bar.date if hasattr(ib_bar, "date") else datetime.now(),
            open=Decimal(str(ib_bar.open)),
            high=Decimal(str(ib_bar.high)),
            low=Decimal(str(ib_bar.low)),
            close=Decimal(str(ib_bar.close)),
            volume=int(ib_bar.volume),
        )

    def _map_interval_to_ib_bar_size(self, interval: TimeInterval) -> str:
        """Map our TimeInterval to IB bar size string."""
        seconds = interval.seconds
        
        if seconds < 60:
            return f"{seconds} secs"
        elif seconds < 3600:
            return f"{seconds // 60} mins"
        elif seconds < 86400:
            return f"{seconds // 3600} hours"
        else:
            return f"{seconds // 86400} days"

    def _calculate_duration(self, start: datetime, end: datetime) -> str:
        """Calculate IB duration string from start/end dates."""
        duration_seconds = (end - start).total_seconds()
        
        if duration_seconds < 86400:
            return f"{int(duration_seconds)} S"
        else:
            return f"{int(duration_seconds / 86400)} D"
