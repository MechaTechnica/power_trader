"""Application lifecycle management."""

import asyncio
import signal
from collections.abc import Awaitable, Callable
from typing import Any

from power_trader_framework.core.di_container import DIContainer


class Application:
    """
    Main application class for bootstrapping and lifecycle management.
    
    Manages:
    - Application startup/shutdown hooks
    - Signal handling (SIGINT, SIGTERM)
    - Graceful shutdown
    - Error handling
    """

    def __init__(self, container: DIContainer) -> None:
        """
        Initialize application.
        
        Args:
            container: DI container with all dependencies registered
        """
        self.container = container
        self._startup_hooks: list[Callable[[], Awaitable[None]]] = []
        self._shutdown_hooks: list[Callable[[], Awaitable[None]]] = []
        self._running = False
        self._shutdown_event = asyncio.Event()

    def on_startup(self, func: Callable[[], Awaitable[None]]) -> None:
        """
        Register a startup hook.
        
        Args:
            func: Async function to call on startup
        """
        self._startup_hooks.append(func)

    def on_shutdown(self, func: Callable[[], Awaitable[None]]) -> None:
        """
        Register a shutdown hook.
        
        Args:
            func: Async function to call on shutdown
        """
        self._shutdown_hooks.append(func)

    async def start(self) -> None:
        """
        Start the application.
        
        Executes all startup hooks in registration order.
        """
        self._running = True
        for hook in self._startup_hooks:
            await hook()

    async def stop(self) -> None:
        """
        Stop the application.
        
        Executes all shutdown hooks in reverse registration order.
        """
        if not self._running:
            return
            
        self._running = False
        
        # Execute shutdown hooks in reverse order
        for hook in reversed(self._shutdown_hooks):
            try:
                await hook()
            except Exception as e:
                # Log error but continue shutdown
                print(f"Error during shutdown hook: {e}")
        
        self._shutdown_event.set()

    async def run(self) -> None:
        """
        Run the application until shutdown.
        
        Handles:
        - Signal handling (SIGINT, SIGTERM)
        - Graceful shutdown
        - Error propagation
        """
        # Set up signal handlers
        loop = asyncio.get_running_loop()
        
        def signal_handler() -> None:
            """Handle shutdown signals."""
            if self._running:
                asyncio.create_task(self.stop())
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)
        
        try:
            # Start application
            await self.start()
            
            # Wait for shutdown
            await self._shutdown_event.wait()
            
        finally:
            # Clean up signal handlers
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.remove_signal_handler(sig)

    async def run_until_complete(self, coro: Awaitable[Any]) -> Any:
        """
        Run application and execute a coroutine.
        
        Args:
            coro: Coroutine to execute
            
        Returns:
            Result of coroutine
        """
        try:
            await self.start()
            return await coro
        finally:
            await self.stop()

    @property
    def is_running(self) -> bool:
        """Check if application is running."""
        return self._running
