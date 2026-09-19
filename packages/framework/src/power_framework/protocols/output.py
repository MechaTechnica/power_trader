"""Generic output/presentation protocols (domain-agnostic)."""

from typing import Protocol


class OutputPresenter(Protocol):
    """Protocol for presenting generic status, warning, and error messages.

    This intentionally does not know about trading concepts. Signal
    presentation is the domain-specific ``SignalPresenter`` protocol in
    ``power_market.protocols.output``; concrete adapters may implement both.
    """

    async def present_error(self, error: Exception) -> None:
        """
        Present an error to the user.

        Args:
            error: Exception that occurred
        """
        ...

    async def present_status(self, message: str) -> None:
        """
        Present a status message to the user.

        Args:
            message: Status message (e.g., "Connected to broker")
        """
        ...

    async def present_warning(self, message: str) -> None:
        """
        Present a warning message to the user.

        Args:
            message: Warning message
        """
        ...
