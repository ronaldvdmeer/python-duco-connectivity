"""Tests for the public exceptions."""

from duco_connectivity import (
    DucoConnectionError,
    DucoError,
    DucoRateLimitError,
    DucoWriteLimitError,
)


def test_connection_error_inherits_from_base_error() -> None:
    """DucoConnectionError should remain catchable as DucoError."""
    err = DucoConnectionError("unreachable")
    assert isinstance(err, DucoError)


def test_write_limit_error_inherits_from_base_error() -> None:
    """DucoWriteLimitError should remain catchable as DucoError."""
    err = DucoWriteLimitError(remaining=5)
    assert isinstance(err, DucoError)


def test_write_limit_error_stores_remaining_count() -> None:
    """DucoWriteLimitError should expose the remaining count when present."""
    err = DucoWriteLimitError(remaining=10)
    assert err.remaining == 10
    assert "10" in str(err)


def test_rate_limit_error_alias_points_to_write_limit_error() -> None:
    """The old rate-limit exception name should remain import-compatible."""
    assert DucoRateLimitError is DucoWriteLimitError
    err = DucoRateLimitError(remaining=3)
    assert isinstance(err, DucoWriteLimitError)
    assert err.remaining == 3
