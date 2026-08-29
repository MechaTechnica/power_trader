"""Application exceptions."""


class ApplicationError(Exception):
    """Base exception for application errors."""

    pass


class ConfigurationError(ApplicationError):
    """Raised when configuration is invalid or missing."""

    pass


class ConnectionError(ApplicationError):
    """Raised when connection to external service fails."""

    pass


class PluginError(ApplicationError):
    """Raised when plugin loading or execution fails."""

    pass


class StrategyError(ApplicationError):
    """Raised when strategy execution fails."""

    pass


class DIError(ApplicationError):
    """Raised when dependency injection fails."""

    pass
