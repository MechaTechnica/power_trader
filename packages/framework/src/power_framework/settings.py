"""Framework settings: shared configuration for every application.

Configuration is a framework concern. An application declares its settings as a
data model and the framework loads it (env + optional JSON file)::

    class PowerTraderSettings(Settings):
        ib: InteractiveBrokersSettings

Declare the model on a plugin via ``settings_class``; the framework registers it
in the container before wiring.
"""

import os
from enum import StrEnum
from pathlib import Path
from typing import ClassVar, TypeVar

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class Environment(StrEnum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    """Root log level."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Settings that may be overridden by an optional JSON file.

    Precedence (highest first): constructor args, env vars, ``.env``, the JSON
    file, then field defaults. Locate the JSON file via ``CONFIG_FILE_ENV`` (an
    env var pointing to a path) or ``DEFAULT_JSON_FILE`` (a path relative to the
    working directory).
    """

    CONFIG_FILE_ENV: ClassVar[str] = ""
    DEFAULT_JSON_FILE: ClassVar[str] = ""

    @classmethod
    def _json_file(cls) -> str | None:
        """Return the JSON config path to load, or ``None`` if not available."""
        path = os.environ.get(cls.CONFIG_FILE_ENV) if cls.CONFIG_FILE_ENV else None
        if not path:
            path = cls.DEFAULT_JSON_FILE or None
        if path and Path(path).exists():
            return path
        return None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Insert the optional JSON source below env vars but above defaults."""
        sources: list[PydanticBaseSettingsSource] = [
            init_settings,
            env_settings,
            dotenv_settings,
        ]
        json_file = cls._json_file()
        if json_file is not None:
            sources.append(
                JsonConfigSettingsSource(settings_cls, json_file=json_file, deep_merge=True)
            )
        sources.append(file_secret_settings)
        return tuple(sources)


class TelemetrySettings(BaseSettings):
    """Telemetry/observability configuration."""

    enabled: bool = Field(
        default=False,
        description="Whether telemetry export is enabled",
    )
    endpoint: str | None = Field(
        default=None,
        description="Optional OTLP/trace collector endpoint",
    )
    sample_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Fraction of spans/events to sample (0.0 - 1.0)",
    )

    model_config = SettingsConfigDict(env_prefix="TELEMETRY_", case_sensitive=False)


class FrameworkSettings(Settings):
    """Framework-level settings shared by every application.

    These are the cross-cutting concerns every application needs: deployment
    environment, service identity, logging, telemetry, plugin discovery, and
    graceful-shutdown behaviour.
    """

    CONFIG_FILE_ENV = "POWER_FRAMEWORK_CONFIG_FILE"
    DEFAULT_JSON_FILE = "framework-settings.json"

    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Deployment environment (development, staging, production)",
    )
    service_name: str = Field(
        default="power-trader",
        description="Name of the running service (used in logs/telemetry)",
    )
    service_version: str = Field(
        default="0.1.0",
        description="Semantic version of the running service (included in telemetry)",
    )
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Root log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    telemetry: TelemetrySettings = Field(
        default_factory=TelemetrySettings,
        description="Telemetry/observability configuration",
    )
    plugin_discovery_enabled: bool = Field(
        default=True,
        description="Whether the plugin registry should auto-discover installed plugins",
    )
    enabled_plugins: list[str] | None = Field(
        default=None,
        description=(
            "Explicit allowlist of plugin names to authorize. When None, all "
            "discovered plugins are authorized; set a list to restrict which "
            "installed plugins are loaded and executed (discovery != authorization)."
        ),
    )
    shutdown_timeout_seconds: float = Field(
        default=10.0,
        description="Maximum time to wait for graceful shutdown hooks to complete",
    )

    model_config = SettingsConfigDict(
        env_prefix="POWER_FRAMEWORK_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )


SettingsT = TypeVar("SettingsT", bound=Settings)


def load_settings(settings_type: type[SettingsT]) -> SettingsT:
    """Load a settings model from environment and optional JSON file.

    This is the framework's single configuration entry point. Applications
    declare their settings type (via ``Plugin.settings_class``) and the
    framework loads it, rather than each plugin instantiating its own settings
    and re-inventing precedence rules.

    Follow up for this method could be:
     _apply_secret_provider(settings)    # resolve refs from Key Vault
     _validate_for_environment(settings) # fail fast in prod
    """
    return settings_type()


__all__ = [
    "Environment",
    "FrameworkSettings",
    "LogLevel",
    "Settings",
    "TelemetrySettings",
    "load_settings",
]
