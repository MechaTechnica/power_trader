from power_day_trader.application import PowerDayTraderApplication
from power_framework.application import ApplicationBuilder


def main() -> None:
    runtime = ApplicationBuilder(PowerDayTraderApplication).build()
    runtime.run()


if __name__ == "__main__":
    main()
