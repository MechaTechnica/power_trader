"""Framework-level settings shared by every Power Trader application.

These settings capture concerns that belong to the *framework* rather than
to any specific trading application: logging, environment, plugin discovery,
and other cross-cutting infrastructure concerns. Application-specific
settings (e.g. broker credentials, trading parameters) belong in the
application package instead and should typically compose ``FrameworkSettings``
alongside their own application settings.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FrameworkSettings(BaseSettings):
    """Settings for the Power Trader framework runtime.

    Controlled via environment variables prefixed with ``POWER_FRAMEWORK_``,
    e.g. ``POWER_FRAMEWORK_LOG_LEVEL=DEBUG``.
    """

    environment: str = Field(
        default="development",
        description="Deployment environment (development, staging, production)",
    )
    log_level: str = Field(
        default="INFO",
        description="Root log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    plugin_discovery_enabled: bool = Field(
        default=True,
        description="Whether the plugin registry should auto-discover strategies",
    )
    shutdown_timeout_seconds: float = Field(
        default=10.0,
        description="Maximum time to wait for graceful shutdown hooks to complete",
    )

    model_config = SettingsConfigDict(
        env_prefix="POWER_FRAMEWORK_",
        case_sensitive=False,
    )

    @classmethod
    def load(cls) -> "FrameworkSettings":
        """Load framework settings from environment."""
        return cls()
