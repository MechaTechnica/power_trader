"""Application lifecycle management implementation."""

import asyncio
import signal
from collections.abc import Awaitable, Callable
from typing import Any

from power_core.container import Container


class Application:
    """
    Application lifecycle manager.
    
    Manages:
    - Startup/shutdown hooks
    - Signal handling (SIGINT, SIGTERM)
    - Graceful shutdown
    - Error handling
    """

    def __init__(self, container: Container) -> None:
        """Initialize application with DI container."""
        self.container = container
        self._startup_hooks: list[Callable[[], Awaitable[None]]] = []
        self._shutdown_hooks: list[Callable[[], Awaitable[None]]] = []
        self._running = False
        self._shutdown_event = asyncio.Event()

    def on_startup(self, func: Callable[[], Awaitable[None]]) -> None:
        """Register a startup hook."""
        self._startup_hooks.append(func)

    def on_shutdown(self, func: Callable[[], Awaitable[None]]) -> None:
        """Register a shutdown hook."""
        self._shutdown_hooks.append(func)

    async def start(self) -> None:
        """Start the application - executes all startup hooks."""
        self._running = True
        for hook in self._startup_hooks:
            await hook()

    async def stop(self) -> None:
        """Stop the application - executes all shutdown hooks in reverse."""
        if not self._running:
            return
            
        self._running = False
        
        for hook in reversed(self._shutdown_hooks):
            try:
                await hook()
            except Exception as e:
                print(f"Error during shutdown hook: {e}")
        
        self._shutdown_event.set()

    async def run(self) -> None:
        """Run the application until shutdown signal."""
        loop = asyncio.get_running_loop()
        
        def signal_handler() -> None:
            if self._running:
                asyncio.create_task(self.stop())
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)
        
        try:
            await self.start()
            await self._shutdown_event.wait()
        finally:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.remove_signal_handler(sig)

    async def run_until_complete(self, coro: Awaitable[Any]) -> Any:
        """Run application and execute a coroutine."""
        try:
            await self.start()
            return await coro
        finally:
            await self.stop()

    @property
    def is_running(self) -> bool:
        """Check if application is running."""
        return self._running
