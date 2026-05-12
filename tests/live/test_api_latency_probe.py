"""Opt-in latency probe for repeated live GET /api calls."""

import asyncio
import math
from collections.abc import Callable
from statistics import fmean
from time import perf_counter

import pytest

from duco_connectivity import DucoClient

pytestmark = [pytest.mark.live, pytest.mark.performance]


def _percentile(samples: list[float], fraction: float) -> float:
    """Return the interpolated percentile for a non-empty sample list."""
    ordered = sorted(samples)
    if len(ordered) == 1:
        return ordered[0]

    index = (len(ordered) - 1) * fraction
    lower_index = math.floor(index)
    upper_index = math.ceil(index)
    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]

    if lower_index == upper_index:
        return lower_value

    return lower_value + (upper_value - lower_value) * (index - lower_index)


async def test_live_api_latency_probe(
    live_client: DucoClient,
    live_report: Callable[[str], None],
    live_api_probe_samples: int,
    live_api_probe_interval: float,
) -> None:
    """Measure repeated live GET /api calls at a steady interval."""
    latencies: list[float] = []
    api_versions: list[str] = []

    warmup_response = await live_client.async_get_api_info()
    assert warmup_response.public_api_version

    probe_started = perf_counter()

    for sample_number in range(live_api_probe_samples):
        request_started = perf_counter()
        api_info = await live_client.async_get_api_info()
        elapsed = perf_counter() - request_started

        latencies.append(elapsed)
        api_versions.append(api_info.public_api_version)

        if sample_number < live_api_probe_samples - 1:
            await asyncio.sleep(max(0.0, live_api_probe_interval - elapsed))

    probe_elapsed = perf_counter() - probe_started

    live_report(
        "api_latency "
        f"samples={live_api_probe_samples} "
        f"interval={live_api_probe_interval:.2f}s "
        f"min={min(latencies):.3f}s "
        f"avg={fmean(latencies):.3f}s "
        f"p50={_percentile(latencies, 0.50):.3f}s "
        f"p95={_percentile(latencies, 0.95):.3f}s "
        f"max={max(latencies):.3f}s "
        f"elapsed={probe_elapsed:.3f}s "
        f"api={api_versions[-1]}"
    )

    assert len(latencies) == live_api_probe_samples
    assert all(latency > 0 for latency in latencies)
    assert all(version for version in api_versions)
