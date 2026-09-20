"""Framework settings: shared configuration capability for every application.

Configuration is a *framework* concern, not an application concern. The
framework owns the vocabulary (environment, service name, logging, telemetry)
and the loading mechanism, so applications get consistent behaviour without
each team re-inventing it.

An application only *declares* its own settings as a data model::

    class PowerTraderSettings(Settings):
        ib: InteractiveBrokersSettings

and declares it on its plugin via ``settings_class``. The framework then loads
both :class:`FrameworkSettings` and the application settings, registering them
in the container before the plugin wires anything up.
"""

import os
from enum import Enum
from typing import ClassVar, TypeVar

from pydantic import Field
from pydantic_settings import (BaseSettings, JsonConfigSettingsSource,
                               PydanticBaseSettingsSource, SettingsConfigDict)


class Environment(str, Enum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Root log level."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """
    Base settings model that can load overrides from an external JSON file.

    This lets operators adjust configuration at runtime without repackaging
    the application: the JSON file is read from disk when settings are
    instantiated, and it is *optional* - if absent, only defaults and
    environment variables are used.

    When the JSON file is present, values are resolved with the following
    precedence (highest first):

    1. Values passed directly to the constructor (``__init__``).
    2. Environment variables (``env_prefix`` / ``env_nested_delimiter``).
    3. ``.env`` files.
    4. The JSON file.
    5. Field defaults.

    Subclasses configure the JSON lookup with two class attributes:

    - ``CONFIG_FILE_ENV``: name of an environment variable that points to an
      explicit JSON path (used first when set).
    - ``DEFAULT_JSON_FILE``: a filename resolved relative to the current
      working directory (used when ``CONFIG_FILE_ENV`` is unset).
    """

    CONFIG_FILE_ENV: ClassVar[str] = ""
    DEFAULT_JSON_FILE: ClassVar[str] = ""

    @classmethod
    def _json_file(cls) -> str | None:
        """Return the JSON config path to load, or ``None`` if not available."""
        path = os.environ.get(cls.CONFIG_FILE_ENV) if cls.CONFIG_FILE_ENV else None
        if not path:
            path = cls.DEFAULT_JSON_FILE or None
        if path and os.path.exists(path):
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
                JsonConfigSettingsSource(
                    settings_cls, json_file=json_file, deep_merge=True
                )
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
        description="Whether the plugin registry should auto-discover strategies",
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


TSettings = TypeVar("TSettings", bound=Settings)


def load_settings(settings_type: type[TSettings]) -> TSettings:
    """Load a settings model from environment and optional JSON file.

    This is the framework's single configuration entry point. Applications
    declare their settings type (via ``Plugin.settings_class``) and the
    framework loads it, rather than each plugin instantiating its own settings
    and re-inventing precedence rules.
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
