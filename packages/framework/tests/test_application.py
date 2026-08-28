"""Tests for application lifecycle management."""

import asyncio

import pytest

from power_trader_framework.core.application import Application
from power_trader_framework.core.di_container import DIContainer


class TestApplication:
    """Tests for Application class."""

    async def test_startup_hooks(self) -> None:
        """Test that startup hooks are called."""
        container = DIContainer()
        app = Application(container)
        
        called = []
        
        async def hook1() -> None:
            called.append("hook1")
        
        async def hook2() -> None:
            called.append("hook2")
        
        app.on_startup(hook1)
        app.on_startup(hook2)
        
        await app.start()
        
        assert called == ["hook1", "hook2"]

    async def test_shutdown_hooks(self) -> None:
        """Test that shutdown hooks are called in reverse order."""
        container = DIContainer()
        app = Application(container)
        
        called = []
        
        async def hook1() -> None:
            called.append("hook1")
        
        async def hook2() -> None:
            called.append("hook2")
        
        app.on_shutdown(hook1)
        app.on_shutdown(hook2)
        
        await app.start()
        await app.stop()
        
        # Shutdown hooks should be called in reverse order
        assert called == ["hook2", "hook1"]

    async def test_stop_idempotent(self) -> None:
        """Test that stop() can be called multiple times safely."""
        container = DIContainer()
        app = Application(container)
        
        called_count = 0
        
        async def hook() -> None:
            nonlocal called_count
            called_count += 1
        
        app.on_shutdown(hook)
        
        await app.start()
        await app.stop()
        await app.stop()  # Second call
        
        # Hook should only be called once
        assert called_count == 1

    async def test_is_running(self) -> None:
        """Test is_running property."""
        container = DIContainer()
        app = Application(container)
        
        assert not app.is_running
        
        await app.start()
        assert app.is_running
        
        await app.stop()
        assert not app.is_running

    async def test_run_until_complete(self) -> None:
        """Test run_until_complete method."""
        container = DIContainer()
        app = Application(container)
        
        startup_called = False
        shutdown_called = False
        
        async def on_startup() -> None:
            nonlocal startup_called
            startup_called = True
        
        async def on_shutdown() -> None:
            nonlocal shutdown_called
            shutdown_called = True
        
        app.on_startup(on_startup)
        app.on_shutdown(on_shutdown)
        
        async def task() -> str:
            return "result"
        
        result = await app.run_until_complete(task())
        
        assert result == "result"
        assert startup_called
        assert shutdown_called

    async def test_shutdown_hook_error_continues(self) -> None:
        """Test that errors in shutdown hooks don't stop other hooks."""
        container = DIContainer()
        app = Application(container)
        
        called = []
        
        async def hook1() -> None:
            called.append("hook1")
        
        async def hook2() -> None:
            raise Exception("Error in hook2")
        
        async def hook3() -> None:
            called.append("hook3")
        
        app.on_shutdown(hook1)
        app.on_shutdown(hook2)
        app.on_shutdown(hook3)
        
        await app.start()
        await app.stop()
        
        # hook3 and hook1 should be called (reverse order), even though hook2 errors
        assert "hook3" in called
        assert "hook1" in called
