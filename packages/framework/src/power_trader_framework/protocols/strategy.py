"""Strategy protocols for ML trading strategies."""

from typing import Protocol

from power_trader_framework.types.market import MarketBar
from power_trader_framework.types.signals import TradingSignal


class IStrategy(Protocol):
    """
    Protocol for ML trading strategies (plugins).
    
    Each strategy is a separate package that implements this protocol.
    Strategies are discovered and loaded dynamically via entry points.
    """

    @property
    def strategy_name(self) -> str:
        """
        Unique identifier for this strategy.
        
        Returns:
            Strategy name (e.g., "momentum-v1")
        """
        ...

    @property
    def version(self) -> str:
        """
        Strategy version.
        
        Returns:
            Version string (e.g., "1.0.0")
        """
        ...

    async def analyze(self, bars: list[MarketBar]) -> TradingSignal:
        """
        Analyze market data and generate trading signal.
        
        Args:
            bars: Historical market bars (ordered oldest to newest)
                  The last bar is the most recent
                  
        Returns:
            TradingSignal with BUY, HOLD, or SELL recommendation
            
        Note:
            This is called frequently (hot path), so performance matters.
            Strategies should:
            - Cache computed indicators when possible
            - Avoid blocking I/O
            - Return quickly (< 100ms ideal)
        """
        ...

    async def initialize(self) -> None:
        """
        Initialize strategy.
        
        Called once when strategy is loaded.
        Use for:
        - Loading ML models
        - Warming up caches
        - Validating configuration
        """
        ...

    async def cleanup(self) -> None:
        """
        Cleanup strategy resources.
        
        Called when strategy is unloaded or application shuts down.
        """
        ...


class ISignalAggregator(Protocol):
    """
    Protocol for aggregating signals from multiple strategies.
    
    When multiple strategies provide signals for the same stock,
    this combines them into a single signal using business rules.
    """

    def aggregate_signals(
        self,
        signals: list[TradingSignal],
    ) -> TradingSignal:
        """
        Combine multiple strategy signals into one.
        
        Args:
            signals: List of signals from different strategies
                     All signals are for the same stock/timestamp
                     
        Returns:
            Aggregated signal
            
        Note:
            Implementation defines the aggregation strategy:
            - Weighted average by confidence
            - Unanimous decision only
            - Majority voting
            - Custom ML-based aggregation
        """
        ...
