"""Terminal output adapter using rich library."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from power_market.types.market import TickerSymbol
from power_market.types.signals import Signal, SignalIntent, SignalMetadata


class TerminalOutputAdapter:
    """
    Terminal output implementation using rich library.

    Implements OutputPresenter (generic messages) and SignalPresenter
    (signal presentation) protocols.
    """

    def __init__(self) -> None:
        """Initialize console."""
        self.console = Console()

    def present_signal(
        self,
        symbol: TickerSymbol,
        signal: Signal,
        metadata: SignalMetadata,
    ) -> None:
        del metadata
        """Present a trading signal in formatted table."""
        # Choose color based on signal intent
        if signal.intent == SignalIntent.BUY:
            color = "green"
            emoji = "📈"
        elif signal.intent == SignalIntent.SELL:
            color = "red"
            emoji = "📉"
        else:
            color = "yellow"
            emoji = "➡️"

        # Create table
        table = Table(title=f"{emoji} {symbol} - {signal.intent.value.upper()}")

        table.add_column("Property", style="cyan")
        table.add_column("Value", style=color)

        table.add_row("Confidence", f"{signal.confidence:.1%}")
        table.add_row("Strategy", signal.source.strategy)
        table.add_row("Time", signal.generated_at.strftime("%H:%M:%S"))

        # Add metadata if available
        for key, value in signal.metadata.items():
            if isinstance(value, (int, float)):
                table.add_row(key.title(), f"{value}")
            elif isinstance(value, str):
                table.add_row(key.title(), value)

        self.console.print(table)
        self.console.print()  # Empty line

    def present_error(self, error: Exception) -> None:
        """Present an error message."""
        self.console.print(
            Panel(
                f"[bold red]Error:[/bold red] {error!s}",
                border_style="red",
            )
        )

    def present_status(self, message: str) -> None:
        """Present a status message."""
        self.console.print(f"[bold blue]ℹ️  {message}[/bold blue]")

    def present_warning(self, message: str) -> None:
        """Present a warning message."""
        self.console.print(f"[bold yellow]⚠️  {message}[/bold yellow]")
