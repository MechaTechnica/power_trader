"""Framework exceptions."""


class FrameworkError(Exception):
    """Base exception for all framework errors."""

    pass


class ConfigurationError(FrameworkError):
    """Raised when configuration is invalid or missing."""

    pass


class ConnectionError(FrameworkError):
    """Raised when connection to external service fails."""

    pass


class PluginError(FrameworkError):
    """Raised when plugin loading or execution fails."""

    pass


class StrategyError(FrameworkError):
    """Raised when strategy execution fails."""

    pass


class DIError(FrameworkError):
    """Raised when dependency injection fails."""

    pass
