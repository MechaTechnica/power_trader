"""Terminal output adapter using rich library."""

from datetime import datetime

from power_trader_framework.protocols.output import OutputPresenter
from power_trader_framework.types.market import TickerSymbol
from power_trader_framework.types.signals import (SignalMetadata, SignalType,
                                                  TradingSignal)
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


class TerminalOutputAdapter:
    """
    Terminal output implementation using rich library.
    
    Implements OutputPresenter protocol.
    """

    def __init__(self) -> None:
        """Initialize console."""
        self.console = Console()

    async def present_signal(
        self,
        symbol: TickerSymbol,
        signal: TradingSignal,
        metadata: SignalMetadata,
    ) -> None:
        """Present a trading signal in formatted table."""
        # Choose color based on signal type
        if signal.signal_type == SignalType.BUY:
            color = "green"
            emoji = "📈"
        elif signal.signal_type == SignalType.SELL:
            color = "red"
            emoji = "📉"
        else:
            color = "yellow"
            emoji = "➡️"
        
        # Create table
        table = Table(title=f"{emoji} {symbol} - {signal.signal_type.value.upper()}")
        
        table.add_column("Property", style="cyan")
        table.add_column("Value", style=color)
        
        table.add_row("Confidence", f"{signal.confidence:.1%}")
        table.add_row("Strategy", signal.strategy_name)
        table.add_row("Time", signal.timestamp.strftime("%H:%M:%S"))
        
        # Add metadata if available
        for key, value in signal.metadata.items():
            if isinstance(value, (int, float)):
                table.add_row(key.title(), f"{value}")
            elif isinstance(value, str):
                table.add_row(key.title(), value)
        
        self.console.print(table)
        self.console.print()  # Empty line

    async def present_error(self, error: Exception) -> None:
        """Present an error message."""
        self.console.print(
            Panel(
                f"[bold red]Error:[/bold red] {str(error)}",
                border_style="red",
            )
        )

    async def present_status(self, message: str) -> None:
        """Present a status message."""
        self.console.print(f"[bold blue]ℹ️  {message}[/bold blue]")

    async def present_warning(self, message: str) -> None:
        """Present a warning message."""
        self.console.print(f"[bold yellow]⚠️  {message}[/bold yellow]")
