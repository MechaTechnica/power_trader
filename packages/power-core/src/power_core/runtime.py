"""Concrete application run-loop owner (the runtime implementation).

``power_framework.application`` defines the ``Runtime`` contract (a ``Protocol``)
and ``ApplicationBase``. This module provides the concrete ``Runtime`` that the
runtime package (power-core) constructs and registers in the container during
``create_container``.
"""

import asyncio
from collections.abc import Awaitable

from power_framework.application import ApplicationBase, AsyncApplicationBase
from power_framework.exceptions import FrameworkError


class Runtime:
    """Owns the application run loop on a single event loop.

    Concrete implementation of the ``power_framework.application.Runtime``
    protocol, registered in the container by ``power_core.bootstrap``.
    """

    def __init__(self, *, shutdown_timeout_seconds: float | None = None) -> None:
        self._application: ApplicationBase | None = None
        self._shutdown_timeout_seconds = shutdown_timeout_seconds

    def attach(self, application: ApplicationBase) -> None:
        """Attach the resolved application."""
        self._application = application

    @property
    def application(self) -> ApplicationBase:
        application = self._application
        if application is None:
            raise FrameworkError("No application has been attached to the runtime.")
        return application

    @staticmethod
    async def _invoke(result: Awaitable[None] | None) -> None:
        """Await a lifecycle result when it is a coroutine, ignoring sync returns."""
        if isinstance(result, Awaitable):
            await result

    async def start(self) -> None:
        """Start the application (sync or async lifecycle)."""
        try:
            await self._invoke(self.application.start())
        except Exception as exc:
            raise FrameworkError(f"Failed to start application: {exc}") from exc

    async def stop(self) -> None:
        """Stop the application, optionally bounded by the shutdown timeout."""
        try:
            await self._stop_app(self.application)
        except Exception as exc:
            raise FrameworkError(f"Failed to stop application: {exc}") from exc

    async def _stop_app(self, app: ApplicationBase) -> None:
        """Stop the application (sync or async), bounded by the shutdown timeout."""
        result = app.stop()
        if not isinstance(result, Awaitable):
            return
        if self._shutdown_timeout_seconds is None:
            await result
            return
        try:
            await asyncio.wait_for(result, timeout=self._shutdown_timeout_seconds)
        except TimeoutError as exc:
            raise FrameworkError(
                f"Timed out stopping component after {self._shutdown_timeout_seconds}s"
            ) from exc

    def run(self) -> None:
        """Run the application to completion, owning the event loop.

        This is the synchronous public entry point for application developers.
        Because :class:`AsyncApplicationBase` marks an application as
        asynchronous, the runtime dispatches on the application's type: async
        applications are driven on an event loop via :meth:`run_async`, while
        synchronous applications are driven directly without creating a loop.
        """
        if isinstance(self.application, AsyncApplicationBase):
            asyncio.run(self.run_async())
            return
        self._run_sync()

    def _run_sync(self) -> None:
        """Drive a fully synchronous application without an event loop."""
        app = self.application
        try:
            app.start()
        except Exception as exc:
            raise FrameworkError(f"Failed to start application: {exc}") from exc
        try:
            app.run()
        finally:
            try:
                app.stop()
            except Exception as exc:
                raise FrameworkError(f"Failed to stop application: {exc}") from exc

    async def run_async(self) -> None:
        """Run the application on the ambient event loop.

        Use this when the framework is *embedded* inside an already-running event
        loop (another async application, a notebook, or an async test runner),
        where creating a second loop via :meth:`run` would be incorrect.
        """
        await self.start()
        try:
            await self._invoke(self.application.run())
        finally:
            await self.stop()


__all__ = [
    "Runtime",
]
