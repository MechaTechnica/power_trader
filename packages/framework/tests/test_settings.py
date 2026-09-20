"""Tests for the framework configuration capability."""

from power_framework.settings import (
    Environment,
    FrameworkSettings,
    LogLevel,
    Settings,
    TelemetrySettings,
    load_settings,
)


def test_framework_settings_defaults():
    settings = FrameworkSettings()
    assert settings.environment is Environment.DEVELOPMENT
    assert settings.service_name == "power-trader"
    assert settings.log_level is LogLevel.INFO
    assert isinstance(settings.telemetry, TelemetrySettings)
    assert settings.telemetry.enabled is False


def test_load_settings_returns_instance_of_declared_type():
    class AppSettings(Settings):
        foo: str = "bar"

    settings = load_settings(AppSettings)
    assert isinstance(settings, AppSettings)
    assert settings.foo == "bar"


def test_environment_and_log_level_are_string_enums():
    assert Environment.DEVELOPMENT.value == "development"
    assert Environment.PRODUCTION.value == "production"
    assert LogLevel.INFO.value == "INFO"
    assert LogLevel.DEBUG.value == "DEBUG"
