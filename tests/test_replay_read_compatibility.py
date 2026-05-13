"""Replay-based compatibility tests for typed read endpoints."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass
from typing import Any, cast

import aiohttp
import pytest

from duco_connectivity import (
    Config,
    ConfigNodeOverview,
    ConfigSection,
    ConfigValueOptions,
    ConfigValueString,
    ConfigZonesOverview,
    DucoClient,
    InfoZonesOverview,
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


ALLOWED_UNTYPED_REPLAY_REQUESTS = {
    build_replay_request("GET", "/info"),
}
CORE_MULTI_PROFILE_REQUESTS = {
    build_replay_request("GET", "/config"),
    build_replay_request("GET", "/config/nodes"),
    build_replay_request("GET", "/config/zones"),
    build_replay_request("GET", "/info/nodes"),
    build_replay_request("GET", "/info/zones"),
}
FULL_REPLAY_PROFILES = (
    "ducobox-energy-v27",
    "ducobox-focus-v26",
    "silent-connect-v26",
)


def _assert_api_info(parsed: object, payload: object) -> None:
    api_info = cast(Any, parsed)
    api_payload = cast(dict[str, Any], payload)

    assert api_info.public_api_version == api_payload["PublicApiVersion"]["Val"]
    assert api_info.raw_payload is api_payload
    assert len(api_info.endpoints) == len(api_payload.get("ApiInfo", []))

    reported_api_version = api_payload.get("ApiVersion", {}).get("Val")
    assert api_info.reported_api_version == reported_api_version

    for endpoint, endpoint_payload in zip(
        api_info.endpoints,
        api_payload.get("ApiInfo", []),
        strict=True,
    ):
        assert endpoint.url == endpoint_payload["Url"]
        assert endpoint.query_parameters == endpoint_payload.get("QueryParameters", [])
        assert endpoint.raw_payload is endpoint_payload


def _assert_board_info(parsed: object, payload: object) -> None:
    board = cast(Any, parsed)
    board_payload = cast(dict[str, Any], payload)["General"]["Board"]

    assert board.public_api_version == board_payload["PublicApiVersion"]["Val"]
    assert board.box_name == board_payload["BoxName"]["Val"]
    assert board.box_sub_type_name == board_payload["BoxSubTypeName"]["Val"]
    assert board.serial_board_comm == board_payload["SerialBoardComm"]["Val"]
    assert board.time == board_payload["Time"]["Val"]
    assert board.raw_payload is board_payload


def _iter_config_leaf_paths(
    payload: dict[str, Any],
    path: tuple[str, ...] = (),
) -> Iterator[tuple[tuple[str, ...], dict[str, Any]]]:
    for key, value in payload.items():
        if not isinstance(value, dict):
            continue

        next_path = path + (key,)
        if "Val" in value:
            yield next_path, value
            continue

        yield from _iter_config_leaf_paths(value, path=next_path)


def _resolve_config_leaf(config: Config, path: tuple[str, ...]) -> object:
    current: object = config.sections[path[0]]
    for section_name in path[1:]:
        if not isinstance(current, ConfigSection):
            raise AssertionError(f"Expected ConfigSection while resolving {path!r}")
        current = current.entries[section_name]

    return current


def _assert_config(parsed: object, payload: object) -> None:
    config = cast(Config, parsed)
    config_payload = cast(dict[str, Any], payload)

    assert config.raw_payload is config_payload

    for path, leaf_payload in _iter_config_leaf_paths(config_payload):
        leaf = cast(Any, _resolve_config_leaf(config, path))
        assert leaf.value == leaf_payload["Val"]
        assert leaf.raw_payload is leaf_payload

        if "Options" in leaf_payload:
            assert isinstance(leaf, ConfigValueOptions)
            assert leaf.options == tuple(leaf_payload["Options"])

        if isinstance(leaf_payload["Val"], str):
            assert isinstance(leaf, ConfigValueString)


def _assert_node_configs(parsed: object, payload: object) -> None:
    overview = cast(ConfigNodeOverview, parsed)
    nodes_payload = cast(dict[str, Any], payload)["Nodes"]

    assert overview.raw_payload is payload
    assert len(overview.nodes) == len(nodes_payload)

    for node, node_payload in zip(overview.nodes, nodes_payload, strict=True):
        assert node.node_id == node_payload["Node"]
        assert node.raw_payload is node_payload

        name_payload = node_payload.get("Name")
        if name_payload is None:
            assert node.name is None
            continue

        assert node.name is not None
        assert node.name.value == name_payload["Val"]
        assert node.name.raw_payload is name_payload


def _assert_nodes(parsed: object, payload: object) -> None:
    nodes = cast(list[Any], parsed)
    nodes_payload = cast(dict[str, Any], payload)["Nodes"]

    assert len(nodes) == len(nodes_payload)

    for node, node_payload in zip(nodes, nodes_payload, strict=True):
        assert node.node_id == node_payload["Node"]
        assert node.raw_payload is node_payload
        assert node.general.raw_payload is node_payload["General"]
        assert node.general.name == node_payload["General"]["Name"]["Val"]

        ventilation_payload = node_payload.get("Ventilation")
        if ventilation_payload is not None:
            assert node.ventilation is not None
            assert node.ventilation.raw_payload is ventilation_payload
            if "FlowLvlTgt" in ventilation_payload:
                assert node.ventilation.flow_lvl_tgt == ventilation_payload["FlowLvlTgt"]["Val"]

        sensor_payload = node_payload.get("Sensor")
        if sensor_payload is not None:
            assert node.sensor is not None
            assert node.sensor.raw_payload is sensor_payload
            if "Rh" in sensor_payload:
                assert node.sensor.rh == sensor_payload["Rh"]["Val"]
            if "IaqRh" in sensor_payload:
                assert node.sensor.iaq_rh == sensor_payload["IaqRh"]["Val"]
            if "Co2" in sensor_payload:
                assert node.sensor.co2 == sensor_payload["Co2"]["Val"]
            if "Temp" in sensor_payload:
                assert node.sensor.temp == sensor_payload["Temp"]["Val"]


def _assert_zones_config(parsed: object, payload: object) -> None:
    zones = cast(ConfigZonesOverview, parsed)
    zones_payload = cast(dict[str, Any], payload)["Zones"]

    assert zones.raw_payload is payload
    assert len(zones.zones) == len(zones_payload)

    for zone, zone_payload in zip(zones.zones, zones_payload, strict=True):
        assert zone.zone_id == zone_payload["Zone"]
        assert zone.raw_payload is zone_payload

        name_payload = zone_payload.get("DeviceGroupConfig", {}).get("General", {}).get("Name")
        if name_payload is None:
            assert zone.name is None
        else:
            assert zone.name is not None
            assert zone.name.value == name_payload["Val"]
            assert zone.name.raw_payload is name_payload

        expected_groups = zone_payload.get("Groups", [])
        assert len(zone.groups) == len(expected_groups)
        for group, group_payload in zip(zone.groups, expected_groups, strict=True):
            assert group.group_id == group_payload["Group"]
            assert group.raw_payload is group_payload


def _assert_zones_info(parsed: object, payload: object) -> None:
    zones = cast(InfoZonesOverview, parsed)
    zones_payload = cast(dict[str, Any], payload)["Zones"]

    assert zones.raw_payload is payload
    assert len(zones.zones) == len(zones_payload)

    for zone, zone_payload in zip(zones.zones, zones_payload, strict=True):
        assert zone.zone_id == zone_payload["Zone"]
        assert zone.raw_payload is zone_payload
        assert zone.name == (
            zone_payload.get("DeviceGroupConfig", {}).get("General", {}).get("Name", {}).get("Val")
        )

        expected_groups = zone_payload.get("Groups", [])
        assert len(zone.groups) == len(expected_groups)
        for group, group_payload in zip(zone.groups, expected_groups, strict=True):
            assert group.group_id == group_payload["Group"]
            assert group.nodes == (
                group_payload.get("DeviceGroupConfig", {}).get("General", {}).get("Nodes", [])
            )
            assert group.raw_payload is group_payload


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
        request=build_replay_request("GET", "/config/nodes"),
        invoke=lambda client: client.async_get_node_configs(),
        assert_parsed=_assert_node_configs,
    ),
    ReplayReadCase(
        request=build_replay_request("GET", "/config/zones"),
        invoke=lambda client: client.async_get_zones_config(),
        assert_parsed=_assert_zones_config,
    ),
    ReplayReadCase(
        request=build_replay_request("GET", "/info/nodes"),
        invoke=lambda client: client.async_get_nodes(),
        assert_parsed=_assert_nodes,
    ),
    ReplayReadCase(
        request=build_replay_request("GET", "/info/zones"),
        invoke=lambda client: client.async_get_zones_info(),
        assert_parsed=_assert_zones_info,
    ),
)

CASES_BY_REQUEST = {case.request: case for case in REPLAY_READ_CASES}
PROFILE_FIXTURES = {
    profile: load_sanitized_replay_fixture_set(profile)
    for profile in available_sanitized_replay_profiles()
}
COMPATIBILITY_PROFILE_FIXTURES = {
    profile: PROFILE_FIXTURES[profile] for profile in FULL_REPLAY_PROFILES
}
PROFILE_CASES = [
    (profile, CASES_BY_REQUEST[request])
    for profile, fixtures in COMPATIBILITY_PROFILE_FIXTURES.items()
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
    """Every committed typed replay fixture should map to a compatibility check."""
    missing_cases = sorted(
        set(PROFILE_FIXTURES[profile]) - set(CASES_BY_REQUEST) - ALLOWED_UNTYPED_REPLAY_REQUESTS
    )

    assert not missing_cases, [
        f"Add a replay compatibility case for {_format_request(request)}"
        for request in missing_cases
    ]


@pytest.mark.parametrize("profile", FULL_REPLAY_PROFILES)
def test_real_world_profiles_cover_core_typed_replay_requests(profile: str) -> None:
    """The committed real-world profiles should all cover the core typed read set."""
    fixtures = PROFILE_FIXTURES[profile]
    missing_requests = sorted(CORE_MULTI_PROFILE_REQUESTS - set(fixtures))

    assert not missing_requests, [
        f"Missing core replay fixture {_format_request(request)} for {profile}"
        for request in missing_requests
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
