"""Application settings using Pydantic."""

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


class Settings(BaseSettings):
    """Application settings."""

    ib: InteractiveBrokersSettings = Field(default_factory=InteractiveBrokersSettings)
    trading: TradingSettings = Field(default_factory=TradingSettings)

    model_config = SettingsConfigDict(
        env_prefix="POWER_DAY_TRADER_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from environment."""
        return cls()
