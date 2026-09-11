"""Configuration protocols."""

from typing import Any, Protocol


class ConfigProvider(Protocol):
    """
    Protocol for configuration management.
    
    This is architecture-agnostic and can be implemented with:
    - File-based config (TOML, YAML, JSON)
    - Environment variables
    - Remote config services
    - Database
    """

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key (can use dot notation for nested values)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        ...

    def get_section(self, section: str) -> dict[str, Any]:
        """
        Get entire configuration section.
        
        Args:
            section: Section name
            
        Returns:
            Dictionary of configuration values
        """
        ...

    def has(self, key: str) -> bool:
        """
        Check if configuration key exists.
        
        Args:
            key: Configuration key
            
        Returns:
            True if key exists
        """
        ...
