"""Fixtures for opt-in live tests against a local Duco device."""

import asyncio
import os
from collections.abc import AsyncIterator, Callable
from typing import cast

import aiohttp
import pytest

from duco_connectivity import DucoClient


def _read_optional_int_env(name: str) -> int | None:
    """Return an optional integer environment variable."""
    raw_value = os.getenv(name)
    if raw_value in (None, ""):
        return None

    try:
        return int(raw_value)
    except ValueError:
        pytest.fail(f"{name} must be an integer, got {raw_value!r}")


def _read_optional_float_env(name: str, *, default: float) -> float:
    """Return an optional float environment variable."""
    raw_value = os.getenv(name)
    if raw_value in (None, ""):
        return default

    try:
        return float(raw_value)
    except ValueError:
        pytest.fail(f"{name} must be a float, got {raw_value!r}")


def _read_required_int_env(name: str) -> int:
    """Return a required integer environment variable or skip the test."""
    raw_value = os.getenv(name)
    if raw_value in (None, ""):
        pytest.skip(f"{name} is not set")

    try:
        return int(raw_value)
    except ValueError:
        pytest.fail(f"{name} must be an integer, got {raw_value!r}")


@pytest.fixture
def live_host() -> str:
    """Return the configured Duco host or skip the live suite."""
    host = os.getenv("DUCO_TEST_HOST")
    if not host:
        pytest.skip("DUCO_TEST_HOST is not set")
    return host


@pytest.fixture
def live_port() -> int | None:
    """Return the optional Duco port override."""
    return _read_optional_int_env("DUCO_TEST_PORT")


@pytest.fixture
def live_request_timeout() -> float:
    """Return the request timeout for live tests."""
    return _read_optional_float_env("DUCO_TEST_TIMEOUT", default=10.0)


@pytest.fixture
def live_inter_test_delay() -> float:
    """Return the delay inserted after each live test."""
    return _read_optional_float_env("DUCO_TEST_INTER_TEST_DELAY", default=3.0)


@pytest.fixture
def live_api_probe_samples() -> int:
    """Return how many samples the API latency probe should collect."""
    raw_value = os.getenv("DUCO_TEST_API_BENCHMARK_SAMPLES")
    if raw_value in (None, ""):
        return 10

    try:
        samples = int(raw_value)
    except ValueError:
        pytest.fail(f"DUCO_TEST_API_BENCHMARK_SAMPLES must be an integer, got {raw_value!r}")

    if samples < 1:
        pytest.fail("DUCO_TEST_API_BENCHMARK_SAMPLES must be at least 1")

    return samples


@pytest.fixture
def live_api_probe_interval() -> float:
    """Return the interval between API latency probe samples."""
    interval = _read_optional_float_env("DUCO_TEST_API_BENCHMARK_INTERVAL", default=1.0)
    if interval <= 0:
        pytest.fail("DUCO_TEST_API_BENCHMARK_INTERVAL must be greater than 0")

    return interval


@pytest.fixture
def live_state_poll_interval() -> float:
    """Return the polling interval for state-changing live tests."""
    return _read_optional_float_env("DUCO_TEST_STATE_POLL_INTERVAL", default=0.5)


@pytest.fixture
def live_state_poll_attempts() -> int:
    """Return the maximum number of read-back attempts for state changes."""
    raw_value = os.getenv("DUCO_TEST_STATE_POLL_ATTEMPTS")
    if raw_value in (None, ""):
        return 10

    try:
        attempts = int(raw_value)
    except ValueError:
        pytest.fail(f"DUCO_TEST_STATE_POLL_ATTEMPTS must be an integer, got {raw_value!r}")

    if attempts < 1:
        pytest.fail("DUCO_TEST_STATE_POLL_ATTEMPTS must be at least 1")

    return attempts


@pytest.fixture
def live_ventilation_node_id() -> int:
    """Return the target node for ventilation state live tests."""
    return _read_required_int_env("DUCO_TEST_VENTILATION_NODE_ID")


@pytest.fixture
def live_ventilation_target_states() -> tuple[str, ...]:
    """Return the preferred ventilation states to validate in order."""
    raw_value = os.getenv("DUCO_TEST_VENTILATION_TARGET_STATES")
    if raw_value in (None, ""):
        return ("MAN1", "AUTO")

    states = tuple(part.strip() for part in raw_value.split(",") if part.strip())
    if not states:
        pytest.fail("DUCO_TEST_VENTILATION_TARGET_STATES must contain at least one value")

    return states


@pytest.fixture
async def live_session() -> AsyncIterator[aiohttp.ClientSession]:
    """Yield an aiohttp session for live tests."""
    async with aiohttp.ClientSession() as session:
        yield session


@pytest.fixture
async def live_client(
    live_session: aiohttp.ClientSession,
    live_host: str,
    live_port: int | None,
    live_request_timeout: float,
) -> AsyncIterator[DucoClient]:
    """Yield a Duco client configured for the live target."""
    yield DucoClient(
        session=live_session,
        host=live_host,
        port=live_port,
        request_timeout=live_request_timeout,
    )


@pytest.fixture
def live_report(
    request: pytest.FixtureRequest,
    live_host: str,
    live_port: int | None,
) -> Callable[[str], None]:
    """Collect a concise live-test summary line for the pytest terminal summary."""
    target = live_host if live_port is None else f"{live_host}:{live_port}"

    def _report(message: str) -> None:
        report_lines = getattr(request.config, "_duco_live_report_lines", None)
        if report_lines is None:
            report_lines = []
            setattr(request.config, "_duco_live_report_lines", report_lines)

        cast(list[str], report_lines).append(f"[duco-live {target}] {message}")

    return _report


@pytest.fixture(autouse=True)
async def live_test_delay(live_inter_test_delay: float) -> AsyncIterator[None]:
    """Throttle live tests with a delay after each test run."""
    yield
    if live_inter_test_delay > 0:
        await asyncio.sleep(live_inter_test_delay)


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter,
    exitstatus: int,
    config: pytest.Config,
) -> None:
    """Print collected live-test summaries at the end of the pytest run."""
    del exitstatus

    report_lines: list[str] | None = getattr(config, "_duco_live_report_lines", None)
    if not report_lines:
        return

    terminalreporter.write_sep("=", "Duco live summaries")
    for line in report_lines:
        terminalreporter.write_line(line)
