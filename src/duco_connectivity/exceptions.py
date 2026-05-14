"""Exceptions raised by the Duco client."""


class DucoError(Exception):
    """Base class for client errors."""


class DucoConnectionError(DucoError):
    """Raised when the client cannot reach the box."""


class DucoResponseError(DucoError):
    """Raised when the box responds with an HTTP error status."""

    def __init__(
        self,
        status: int,
        path: str,
        body: str = "",
        *,
        message: str | None = None,
    ) -> None:
        self.status = status
        self.path = path
        self.body = body
        detail = message or f"Unexpected response {status} for {path}: {body}"
        super().__init__(detail)


class DucoWriteLimitError(DucoResponseError):
    """Raised when the box rejects writes because its budget is exhausted."""

    def __init__(
        self,
        remaining: int | None = None,
        *,
        path: str = "",
        body: str = "",
    ) -> None:
        self.remaining = remaining
        detail = "Duco write capacity exhausted"
        if remaining is not None:
            detail = f"{detail} ({remaining} writes remaining)"
        super().__init__(429, path, body, message=detail)


# Backward-compatible alias for the old python-duco-client exception name.
DucoRateLimitError = DucoWriteLimitError
