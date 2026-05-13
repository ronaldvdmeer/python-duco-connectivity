"""Replay-based sample-validation tests for core typed read endpoints."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, cast

import aiohttp
import pytest

from duco_connectivity import (
    Config,
    ConfigNodeOverview,
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
    """Typed read method used for committed replay samples."""

    request: ReplayRequest
    invoke: Callable[[DucoClient], Awaitable[object]]
    assert_parsed: Callable[[object, object], None]


# Replay is intentionally narrow in this repository. These requests represent
# the small baseline we want to keep parseable across the committed real-world
# profiles.
MINIMAL_MULTI_PROFILE_REQUESTS = {
    build_replay_request("GET", "/config"),
    build_replay_request("GET", "/config/nodes"),
    build_replay_request("GET", "/config/zones"),
    build_replay_request("GET", "/info/nodes"),
    build_replay_request("GET", "/info/zones"),
}
MINIMAL_REPLAY_PROFILES = (
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


def _assert_config(parsed: object, payload: object) -> None:
    config = cast(Config, parsed)
    config_payload = cast(dict[str, Any], payload)

    assert config.raw_payload is config_payload
    assert set(config.sections) == set(config_payload)


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
MINIMAL_PROFILE_FIXTURES = {
    profile: PROFILE_FIXTURES[profile] for profile in MINIMAL_REPLAY_PROFILES
}
PROFILE_CASES = [
    (profile, CASES_BY_REQUEST[request])
    for profile, fixtures in PROFILE_FIXTURES.items()
    for request in sorted(fixtures)
    if request in CASES_BY_REQUEST
]


@pytest.mark.parametrize("profile", MINIMAL_REPLAY_PROFILES)
def test_real_world_profiles_cover_minimal_replay_requests(profile: str) -> None:
    """The core committed profiles should keep the minimal replay baseline."""
    fixtures = PROFILE_FIXTURES[profile]
    assert MINIMAL_MULTI_PROFILE_REQUESTS <= set(fixtures)


@pytest.mark.parametrize(
    ("profile", "case"),
    PROFILE_CASES,
    ids=[f"{profile}:{case.request.method}-{case.request.path}" for profile, case in PROFILE_CASES],
)
async def test_replay_fixture_parses_through_typed_client(
    profile: str,
    case: ReplayReadCase,
) -> None:
    """Committed replay fixtures should keep the selected core readers parseable."""
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
