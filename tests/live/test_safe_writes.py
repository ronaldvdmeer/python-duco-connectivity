"""Opt-in safe write tests against a live Duco device."""

from collections.abc import Callable

import pytest

from duco_connectivity import ConfigSection, ConfigValue, DucoClient

pytestmark = [pytest.mark.live, pytest.mark.writes]


async def test_live_noop_timezone_write_round_trip(
    live_client: DucoClient,
    live_report: Callable[[str], None],
) -> None:
    """Round-trip the current timezone value through PATCH /config."""
    before_remaining = await live_client.async_get_write_requests_remaining()
    if before_remaining < 1:
        pytest.skip("No Duco write requests remain for a live write test")

    config = await live_client.async_get_config(
        module="General",
        submodule="Time",
        parameter="TimeZone",
    )

    general = config.sections["General"]
    assert isinstance(general, ConfigSection)

    time_config = general.entries["Time"]
    assert isinstance(time_config, ConfigSection)

    time_zone = time_config.entries["TimeZone"]
    assert isinstance(time_zone, ConfigValue)

    result = await live_client.async_set_config(
        {"General": {"Time": {"TimeZone": {"Val": time_zone.value}}}},
        module="General",
        submodule="Time",
        parameter="TimeZone",
    )

    result_general = result.sections["General"]
    assert isinstance(result_general, ConfigSection)

    result_time = result_general.entries["Time"]
    assert isinstance(result_time, ConfigSection)

    result_time_zone = result_time.entries["TimeZone"]
    assert isinstance(result_time_zone, ConfigValue)
    assert result_time_zone.value == time_zone.value

    after_remaining = await live_client.async_get_write_requests_remaining()
    live_report(
        f"timezone_round_trip value={time_zone.value} "
        f"writes_before={before_remaining} writes_after={after_remaining}"
    )
    assert 0 <= after_remaining <= before_remaining
