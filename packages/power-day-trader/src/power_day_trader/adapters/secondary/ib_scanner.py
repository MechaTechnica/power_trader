"""Interactive Brokers market scanner adapter."""

from typing import Any

from ib_insync import IB, ScannerSubscription

from power_market.types.market import TickerSymbol


class InteractiveBrokersScannerAdapter:
    """Market scanner backed by Interactive Brokers."""

    def __init__(self, ib: IB) -> None:
        self._ib = ib

    async def scan_by_criteria(
        self,
        min_volume: int | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        sector: str | None = None,
        **kwargs: Any,
    ) -> list[TickerSymbol]:
        del sector, kwargs
        """Scan for stocks matching the given criteria."""
        sub = ScannerSubscription(
            instrument="STK",
            locationCode="STK.US",
            scanCode="TOP_PERC_GAIN",
        )

        if min_price is not None:
            sub.abovePrice = min_price
        if max_price is not None:
            sub.belowPrice = max_price
        if min_volume is not None:
            sub.aboveVolume = min_volume

        scanner_data = await self._ib.reqScannerDataAsync(sub)

        symbols = []
        for item in scanner_data:
            contract = item.contractDetails.contract
            if contract is None:
                continue
            symbols.append(TickerSymbol(symbol=contract.symbol, exchange=contract.exchange))
        return symbols
