"""Application-specific settings using Pydantic.

Power Day Trader *declares* these settings as a data model; it does not load
them itself. The framework's configuration capability loads both
``FrameworkSettings`` and this model (via ``Plugin.settings_class``) and
registers them in the container before the plugin wires anything up.
"""

from power_framework.settings import Settings
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


class PowerTraderSettings(Settings):
    """
    Power Day Trader application settings.

    Controlled via environment variables prefixed with ``POWER_DAY_TRADER_``
    (e.g. ``POWER_DAY_TRADER_IB__HOST=127.0.0.1``) and optionally an external
    JSON file, so settings can be changed at runtime without repackaging.

    Loading is owned by the framework; the application only declares the shape
    of its configuration.
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
