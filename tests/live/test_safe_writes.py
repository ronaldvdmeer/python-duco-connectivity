"""Opt-in safe write tests against a live Duco device."""

from collections.abc import Callable

import pytest

from duco_connectivity import (
    BypassSupplyTemperatureTarget,
    ConfigSection,
    ConfigValue,
    ConfigValueString,
    DucoClient,
    PatchConfigValue,
    PatchConfigZoneDeviceGroupConfig,
    PatchConfigZoneGeneral,
    PatchConfigZoneStruct,
)

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


async def test_live_noop_zone_name_write_round_trip(
    live_client: DucoClient,
    live_report: Callable[[str], None],
) -> None:
    """Round-trip the current zone name through PATCH /config/zones/{zone}."""
    before_remaining = await live_client.async_get_write_requests_remaining()
    if before_remaining < 1:
        pytest.skip("No Duco write requests remain for a live zone write test")

    zones = await live_client.async_get_zones_config()
    zone = next((item for item in zones.zones if item.name is not None), None)
    if zone is None:
        pytest.skip("No named zones available for a safe live zone write test")

    assert zone.name is not None
    assert isinstance(zone.name, ConfigValueString)

    result = await live_client.async_set_zone_config(
        zone.zone_id,
        PatchConfigZoneStruct(
            device_group_config=PatchConfigZoneDeviceGroupConfig(
                general=PatchConfigZoneGeneral(name=PatchConfigValue(value=zone.name.value))
            )
        ),
        module="DeviceGroupConfig",
        submodule="General",
        parameter="Name",
    )

    assert result.name is not None
    assert isinstance(result.name, ConfigValueString)
    assert result.name.value == zone.name.value

    after_remaining = await live_client.async_get_write_requests_remaining()
    live_report(
        f"zone_name_round_trip zone={zone.zone_id} value={zone.name.value!r} "
        f"writes_before={before_remaining} writes_after={after_remaining}"
    )
    assert 0 <= after_remaining <= before_remaining


async def test_live_noop_bypass_supply_temperature_target_round_trip(
    live_client: DucoClient,
    live_report: Callable[[str], None],
) -> None:
    """Round-trip the current bypass target through the Celsius convenience helper."""
    before_remaining = await live_client.async_get_write_requests_remaining()
    if before_remaining < 1:
        pytest.skip("No Duco write requests remain for a live bypass write test")

    target = None
    for zone_id in range(1, 9):
        target = await live_client.async_get_bypass_supply_temperature_target(zone_id)
        if target is not None:
            break

    if target is None:
        pytest.skip("No bypass supply temperature target available for a safe live write test")

    result = await live_client.async_set_bypass_supply_temperature_target(
        target.zone_id,
        target.value,
    )

    assert isinstance(result, BypassSupplyTemperatureTarget)
    assert result.zone_id == target.zone_id
    assert result.value == target.value

    after_remaining = await live_client.async_get_write_requests_remaining()
    live_report(
        f"bypass_target_round_trip zone={target.zone_id} value={target.value} "
        f"writes_before={before_remaining} writes_after={after_remaining}"
    )
    assert 0 <= after_remaining <= before_remaining
