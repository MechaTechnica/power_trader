"""Application lifecycle protocols."""

from typing import Protocol


class IApplicationLifecycle(Protocol):
    """
    Protocol for application lifecycle management.
    
    Components can implement this to hook into startup/shutdown.
    """

    async def startup(self) -> None:
        """
        Execute startup sequence.
        
        Called when application is starting.
        Use for:
        - Opening connections
        - Loading resources
        - Initializing caches
        """
        ...

    async def shutdown(self) -> None:
        """
        Execute shutdown sequence.
        
        Called when application is stopping.
        Use for:
        - Closing connections
        - Flushing buffers
        - Cleaning up resources
        """
        ...


class IHealthCheck(Protocol):
    """
    Protocol for health checks.
    
    Components can implement this to report their health status.
    """

    async def check_health(self) -> bool:
        """
        Check if component is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        ...

    def get_health_details(self) -> dict[str, any]:
        """
        Get detailed health information.
        
        Returns:
            Dictionary with health details (e.g., connection status, metrics)
        """
        ...
