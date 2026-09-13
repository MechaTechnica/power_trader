"""Main entry point for Power Day Trader."""

from power_day_trader.application import PowerDayTraderApplication
from power_trader_framework.application import ApplicationBuilder


def cli() -> None:
    """Build and run the Power Day Trader application."""
    app = ApplicationBuilder(PowerDayTraderApplication).build()
    app.run()


if __name__ == "__main__":
    cli()
