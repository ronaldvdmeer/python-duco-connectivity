"""Replay-based compatibility tests for typed read endpoints."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, cast

import aiohttp
import pytest

from duco_connectivity import (
    Config,
    ConfigSection,
    ConfigValue,
    ConfigValueOptions,
    ConfigValueString,
    DucoClient,
    InfoZonesOverview,
    NodeType,
)
from tests.helpers.replay import (
    ReplayRequest,
    available_sanitized_replay_profiles,
    build_replay_request,
    load_sanitized_replay_fixture_set,
)


@dataclass(frozen=True, slots=True)
class ReplayReadCase:
    """Typed read method backed by a sanitized replay fixture."""

    request: ReplayRequest
    invoke: Callable[[DucoClient], Awaitable[object]]
    assert_parsed: Callable[[object, object], None]


def _assert_api_info(parsed: object, payload: object) -> None:
    api_info = cast(Any, parsed)
    api_payload = cast(dict[str, Any], payload)

    assert api_info.public_api_version == api_payload["PublicApiVersion"]["Val"]
    assert api_info.endpoints == []
    assert api_info.raw_payload is api_payload


def _assert_board_info(parsed: object, payload: object) -> None:
    board = cast(Any, parsed)
    board_payload = cast(dict[str, Any], payload)["General"]["Board"]

    assert board.public_api_version == board_payload["PublicApiVersion"]["Val"]
    assert board.box_name == board_payload["BoxName"]["Val"]
    assert board.box_sub_type_name == board_payload["BoxSubTypeName"]["Val"]
    assert board.serial_board_comm == board_payload["SerialBoardComm"]["Val"]
    assert board.time == board_payload["Time"]["Val"]
    assert board.raw_payload is board_payload


def _assert_config(parsed: object, payload: object) -> None:
    config = cast(Config, parsed)
    config_payload = cast(dict[str, Any], payload)

    assert config.raw_payload is config_payload

    general = config.sections["General"]
    assert isinstance(general, ConfigSection)

    time_section = general.entries["Time"]
    assert isinstance(time_section, ConfigSection)

    time_zone = time_section.entries["TimeZone"]
    assert isinstance(time_zone, ConfigValue)
    assert time_zone.value == config_payload["General"]["Time"]["TimeZone"]["Val"]

    lan_section = general.entries["Lan"]
    assert isinstance(lan_section, ConfigSection)

    mode = lan_section.entries["Mode"]
    assert isinstance(mode, ConfigValueOptions)
    assert mode.options == (1, 2, 4)

    static_ip = lan_section.entries["StaticIp"]
    assert isinstance(static_ip, ConfigValueString)
    assert static_ip.value == config_payload["General"]["Lan"]["StaticIp"]["Val"]


def _assert_nodes(parsed: object, payload: object) -> None:
    nodes = cast(list[Any], parsed)
    nodes_payload = cast(dict[str, Any], payload)["Nodes"]

    assert len(nodes) == len(nodes_payload)

    box = nodes[0]
    assert box.node_id == nodes_payload[0]["Node"]
    assert box.general.node_type == NodeType.BOX
    assert box.ventilation is not None
    assert box.ventilation.flow_lvl_tgt == nodes_payload[0]["Ventilation"]["FlowLvlTgt"]["Val"]
    assert box.sensor is not None
    assert box.sensor.rh == nodes_payload[0]["Sensor"]["Rh"]["Val"]
    assert box.raw_payload is nodes_payload[0]

    second_node = nodes[1]
    assert second_node.node_id == nodes_payload[1]["Node"]
    assert second_node.general.name == nodes_payload[1]["General"]["Name"]["Val"]


def _assert_zones(parsed: object, payload: object) -> None:
    zones = cast(InfoZonesOverview, parsed)
    zones_payload = cast(dict[str, Any], payload)

    assert zones.raw_payload is zones_payload
    assert [zone.zone_id for zone in zones.zones] == [1, 2]
    assert (
        zones.zones[0].name
        == zones_payload["Zones"][0]["DeviceGroupConfig"]["General"]["Name"]["Val"]
    )
    assert zones.zones[0].groups[0].nodes == [7, 8]
    assert zones.zones[0].raw_payload is zones_payload["Zones"][0]
    assert zones.zones[0].groups[0].raw_payload is zones_payload["Zones"][0]["Groups"][0]


REPLAY_READ_CASES = (
    ReplayReadCase(
        request=build_replay_request("GET", "/api"),
        invoke=lambda client: client.async_get_api_info(),
        assert_parsed=_assert_api_info,
    ),
    ReplayReadCase(
        request=build_replay_request(
            "GET",
            "/info",
            params={"module": "General", "submodule": "Board"},
        ),
        invoke=lambda client: client.async_get_board_info(),
        assert_parsed=_assert_board_info,
    ),
    ReplayReadCase(
        request=build_replay_request("GET", "/config"),
        invoke=lambda client: client.async_get_config(),
        assert_parsed=_assert_config,
    ),
    ReplayReadCase(
        request=build_replay_request("GET", "/info/nodes"),
        invoke=lambda client: client.async_get_nodes(),
        assert_parsed=_assert_nodes,
    ),
    ReplayReadCase(
        request=build_replay_request("GET", "/info/zones"),
        invoke=lambda client: client.async_get_zones_info(),
        assert_parsed=_assert_zones,
    ),
)

CASES_BY_REQUEST = {case.request: case for case in REPLAY_READ_CASES}
PROFILE_FIXTURES = {
    profile: load_sanitized_replay_fixture_set(profile)
    for profile in available_sanitized_replay_profiles()
}
PROFILE_CASES = [
    (profile, CASES_BY_REQUEST[request])
    for profile, fixtures in PROFILE_FIXTURES.items()
    for request in sorted(fixtures)
    if request in CASES_BY_REQUEST
]


def _format_request(request: ReplayRequest) -> str:
    details = f"{request.method} {request.path}"
    if not request.params:
        return details

    return f"{details} params={dict(request.params)!r}"


@pytest.mark.parametrize("profile", sorted(PROFILE_FIXTURES))
def test_replay_profiles_register_contract_checks_for_committed_fixtures(
    profile: str,
) -> None:
    """Every committed replay fixture should map to a typed contract check."""
    missing_cases = sorted(set(PROFILE_FIXTURES[profile]) - set(CASES_BY_REQUEST))

    assert not missing_cases, [
        f"Add a replay compatibility case for {_format_request(request)}"
        for request in missing_cases
    ]


@pytest.mark.parametrize(
    ("profile", "case"),
    PROFILE_CASES,
    ids=[f"{profile}:{case.request.method}-{case.request.path}" for profile, case in PROFILE_CASES],
)
async def test_replay_fixture_parses_through_typed_client(
    profile: str,
    case: ReplayReadCase,
) -> None:
    """Committed replay fixtures should parse through the normal typed client methods."""
    fixtures = PROFILE_FIXTURES[profile]
    requested: list[ReplayRequest] = []

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")

        async def _request_json(
            method: str,
            path: str,
            *,
            params: dict[str, object] | None = None,
            **kwargs: object,
        ) -> Any:
            del kwargs

            request = build_replay_request(method, path, params=params)
            requested.append(request)
            return fixtures[request].payload

        client._request_json = _request_json
        parsed = await case.invoke(client)

    assert requested == [case.request]
    case.assert_parsed(parsed, fixtures[case.request].payload)
