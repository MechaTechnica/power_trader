"""Market data protocols."""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, Protocol

from power_market.types.market import MarketBar, TickerSymbol, TimeInterval


class MarketDataProvider(Protocol):
    """A market data source (e.g. Interactive Brokers)."""

    async def start(self) -> None:
        """Establish the connection."""
        ...

    async def stop(self) -> None:
        """Close the connection."""
        ...

    async def stream_bars(
        self,
        symbols: list[TickerSymbol],
        interval: TimeInterval,  # noqa: ARG002 - part of the interface
    ) -> AsyncIterator[MarketBar]:
        """Stream real-time bars for ``symbols`` at ``interval``."""
        ...
        if False:  # pragma: no cover - makes this an async generator
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
        """Return historical bars for ``symbol`` between ``start`` and ``end``."""
        ...


class MarketScanner(Protocol):
    """Discovers tradeable securities matching criteria."""

    async def scan_by_criteria(
        self,
        min_volume: int | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        sector: str | None = None,
        **kwargs: Any,
    ) -> list[TickerSymbol]:
        """Return symbols matching the given criteria."""
        ...
