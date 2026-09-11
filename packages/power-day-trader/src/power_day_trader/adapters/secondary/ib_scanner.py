"""Interactive Brokers market scanner adapter."""

from ib_insync import IB, ScannerSubscription
from power_trader_framework.protocols.data import MarketScanner
from power_trader_framework.types.market import TickerSymbol


class InteractiveBrokersScannerAdapter:
    """
    Interactive Brokers scanner adapter implementing MarketScanner.
    
    Uses IB's market scanner to find stocks matching criteria.
    """

    def __init__(self, ib: IB) -> None:
        """
        Initialize scanner adapter.
        
        Args:
            ib: Connected IB instance (shared with data provider)
        """
        self._ib = ib

    async def scan_by_criteria(
        self,
        min_volume: int | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        sector: str | None = None,
        **kwargs: any,
    ) -> list[TickerSymbol]:
        """
        Scan market using IB scanner.
        
        Note: IB scanner has many parameters. This is a simplified interface.
        """
        # Create scanner subscription
        sub = ScannerSubscription(
            instrument="STK",
            locationCode="STK.US",
            scanCode="TOP_PERC_GAIN",  # Most active by volume
        )
        
        # Apply filters
        if min_price is not None:
            sub.abovePrice = min_price
        if max_price is not None:
            sub.belowPrice = max_price
        if min_volume is not None:
            sub.aboveVolume = min_volume
        
        # Request scanner data
        scanner_data = await self._ib.reqScannerDataAsync(sub)
        
        # Convert to TickerSymbol list
        symbols = []
        for item in scanner_data:
            contract = item.contractDetails.contract
            symbols.append(TickerSymbol(symbol=contract.symbol, exchange=contract.exchange))
        
        return symbols
