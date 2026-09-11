"""Application-specific settings using Pydantic.

Power Day Trader owns these settings; they are distinct from
``power_trader_framework.settings.FrameworkSettings``, which holds generic
runtime concerns shared by every Power Trader application. This module holds
settings that only make sense for *this* application (broker connection
details, trading parameters, etc.).
"""

from power_trader_framework.settings import JsonFileSettings
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class InteractiveBrokersSettings(BaseSettings):
    """Interactive Brokers connection settings."""

    host: str = Field(default="127.0.0.1", description="IB Gateway/TWS host")
    port: int = Field(default=7497, description="IB Gateway/TWS port (7497=TWS paper)")
    client_id: int = Field(default=1, description="Client ID")

    model_config = SettingsConfigDict(env_prefix="IB_")


class TradingSettings(BaseSettings):
    """Trading configuration."""

    default_interval_seconds: int = Field(
        default=60, description="Default bar interval in seconds"
    )
    max_concurrent_symbols: int = Field(
        default=10, description="Maximum symbols to monitor concurrently"
    )

    model_config = SettingsConfigDict(env_prefix="TRADING_")


class PowerTraderSettings(JsonFileSettings):
    """
    Power Day Trader application settings.

    Controlled via environment variables prefixed with ``POWER_DAY_TRADER_``
    (e.g. ``POWER_DAY_TRADER_IB__HOST=127.0.0.1``) and optionally an external
    JSON file, so settings can be changed at runtime without repackaging.
    """

    CONFIG_FILE_ENV = "POWER_DAY_TRADER_CONFIG_FILE"
    DEFAULT_JSON_FILE = "power-day-trader-settings.json"

    ib: InteractiveBrokersSettings = Field(default_factory=InteractiveBrokersSettings)
    trading: TradingSettings = Field(default_factory=TradingSettings)

    model_config = SettingsConfigDict(
        env_prefix="POWER_DAY_TRADER_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    @classmethod
    def load(cls) -> "PowerTraderSettings":
        """Load application settings from environment and optional JSON file."""
        return cls()
