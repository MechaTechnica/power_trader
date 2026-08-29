"""Application bootstrap utilities."""

from collections.abc import Awaitable, Callable

from power_core.application import Application
from power_core.di_container import DIContainer


def create_application(
    container: DIContainer,
    on_app_created: Callable[[Application], Awaitable[None]] | None = None,
) -> Application:
    """
    Create and configure an application.
    
    This is a convenience function that:
    1. Creates the Application instance
    2. Calls the on_app_created callback if provided
    3. Returns the configured application
    
    Args:
        container: DI container with all dependencies registered
        on_app_created: Optional callback to configure the app after creation
        
    Returns:
        Configured Application instance
        
    Example:
        ```python
        async def configure_app(app: Application) -> None:
            app.on_startup(my_startup)
            app.on_shutdown(my_shutdown)
        
        app = create_application(container, on_app_created=configure_app)
        await app.run()
        ```
    """
    app = Application(container)
    
    if on_app_created:
        # Note: This is sync, but the callback can be async
        # The callback should register hooks, not execute them
        import asyncio
        asyncio.create_task(on_app_created(app))
    
    return app
