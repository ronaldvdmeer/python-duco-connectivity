"""Tests for the public exceptions."""

import pytest

from duco_connectivity import (
    DucoConnectionError,
    DucoError,
    DucoRateLimitError,
    DucoResponseError,
    DucoUnsupportedCapabilityError,
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


def test_response_error_stores_http_metadata() -> None:
    """DucoResponseError should expose status, path, and body."""
    err = DucoResponseError(404, "/info", "missing")
    assert err.status == 404
    assert err.path == "/info"
    assert err.body == "missing"
    assert str(err) == "Unexpected response 404 for /info: missing"
    assert isinstance(err, DucoError)


@pytest.mark.parametrize("body", ["", "   "])
def test_response_error_omits_empty_body_from_default_message(body: str) -> None:
    """DucoResponseError should omit the body suffix when no body content exists."""
    err = DucoResponseError(404, "/info", body)

    assert str(err) == "Unexpected response 404 for /info"


def test_unsupported_capability_error_preserves_response_context() -> None:
    """DucoUnsupportedCapabilityError should retain HTTP response context."""
    err = DucoUnsupportedCapabilityError(400, "/info", "unsupported")
    assert isinstance(err, DucoResponseError)
    assert err.status == 400
    assert err.path == "/info"
    assert err.body == "unsupported"


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


def test_write_limit_error_exposes_http_metadata() -> None:
    """DucoWriteLimitError should expose HTTP metadata for 429 responses."""
    err = DucoWriteLimitError(path="/config", body="rate limited")
    assert err.status == 429
    assert err.path == "/config"
    assert err.body == "rate limited"
