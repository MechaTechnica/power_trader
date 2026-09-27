"""Domain-agnostic output/presentation contract."""

from typing import Protocol


class OutputPresenter(Protocol):
    """Protocol for presenting generic status, warning, and error messages.

    This intentionally does not know about trading concepts. Signal
    presentation is the domain-specific ``SignalPresenter`` protocol in
    ``power_market.protocols.output``; concrete adapters may implement both.

    These are synchronous operations (e.g. printing to a terminal), so they
    intentionally do not use ``async``; an application may present output
    without being coupled to an event loop.
    """

    def present_error(self, error: Exception) -> None:
        """Present an error to the user.

        Args:
            error: Exception that occurred
        """

    def present_status(self, message: str) -> None:
        """Present a status message to the user.

        Args:
            message: Status message (e.g., "Connected to broker")
        """

    def present_warning(self, message: str) -> None:
        """Present a warning to the user.

        Args:
            message: Warning message
        """


__all__ = [
    "OutputPresenter",
]
