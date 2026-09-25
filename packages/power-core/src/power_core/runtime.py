"""Concrete application run-loop owner (the runtime implementation).

``power_framework.application`` defines the ``Runtime`` contract (a ``Protocol``)
and ``ApplicationBase``. This module provides the concrete ``Runtime`` that the
runtime package (power-core) constructs and registers in the container during
``create_container``.
"""

import asyncio

from power_framework.application import ApplicationBase
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

    async def start(self) -> None:
        """Start the application."""
        try:
            await self.application.start()
        except Exception as exc:
            raise FrameworkError(f"Failed to start application: {exc}") from exc

    async def stop(self) -> None:
        """Stop the application, optionally bounded by the shutdown timeout."""
        try:
            await self._stop_app(self.application)
        except Exception as exc:
            raise FrameworkError(f"Failed to stop application: {exc}") from exc

    async def _stop_app(self, app: ApplicationBase) -> None:
        """Stop the application, optionally bounded by the shutdown timeout."""
        if self._shutdown_timeout_seconds is None:
            await app.stop()
            return
        try:
            await asyncio.wait_for(app.stop(), timeout=self._shutdown_timeout_seconds)
        except TimeoutError as exc:
            raise FrameworkError(
                f"Timed out stopping component after {self._shutdown_timeout_seconds}s"
            ) from exc

    def run(self) -> None:
        """Run the application to completion, owning the event loop.

        This is the synchronous public entry point for application developers.
        Use run_async to run your application aynchronously
        """
        asyncio.run(self.run_async())

    async def run_async(self) -> None:
        """Run the application on the ambient event loop.

        Use this when the framework is *embedded* inside an already-running event
        loop (another async application, a notebook, or an async test runner),
        where creating a second loop via :meth:`run` would be incorrect.
        """
        await self.start()
        try:
            await self.application.run()
        finally:
            await self.stop()


__all__ = [
    "Runtime",
]