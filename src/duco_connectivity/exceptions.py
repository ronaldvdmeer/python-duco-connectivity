"""Exceptions raised by the Duco client."""


class DucoError(Exception):
    """Base class for client errors."""


class DucoConnectionError(DucoError):
    """Raised when the client cannot reach the box."""


class DucoWriteLimitError(DucoError):
    """Raised when the box rejects writes because its budget is exhausted."""

    def __init__(self, remaining: int | None = None) -> None:
        self.remaining = remaining
        detail = "Duco write capacity exhausted"
        if remaining is not None:
            detail = f"{detail} ({remaining} writes remaining)"
        super().__init__(detail)
