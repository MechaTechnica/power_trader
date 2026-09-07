"""Framework-level settings shared by every Power Trader application.

These settings capture concerns that belong to the *framework* rather than
to any specific trading application: logging, environment, plugin discovery,
and other cross-cutting infrastructure concerns. Application-specific
settings (e.g. broker credentials, trading parameters) belong in the
application package instead and should typically compose ``FrameworkSettings``
alongside their own application settings.
"""

import os
from typing import Any, ClassVar

from pydantic import Field
from pydantic_settings import (BaseSettings, JsonConfigSettingsSource,
                               PydanticBaseSettingsSource, SettingsConfigDict)


class JsonFileSettings(BaseSettings):
    """
    Base settings that can load overrides from an external JSON file.

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


class FrameworkSettings(JsonFileSettings):
    """
    Settings for the Power Trader framework runtime.

    Controlled via environment variables prefixed with ``POWER_FRAMEWORK_``
    (e.g. ``POWER_FRAMEWORK_LOG_LEVEL=DEBUG``) and optionally a JSON file
    (see :class:`JsonFileSettings`).
    """

    CONFIG_FILE_ENV = "POWER_FRAMEWORK_CONFIG_FILE"
    DEFAULT_JSON_FILE = "framework-settings.json"

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
        """Load framework settings from environment and optional JSON file."""
        return cls()


__all__ = ["FrameworkSettings", "JsonFileSettings"]
