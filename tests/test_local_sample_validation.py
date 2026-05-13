"""Local-only validation for raw replay sample fixtures."""

from __future__ import annotations

import os
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
    build_replay_request,
    load_local_sample_fixture_set,
)

LOCAL_SAMPLE_PROFILE = os.getenv("DUCO_SAMPLE_PROFILE")

if not LOCAL_SAMPLE_PROFILE:
    pytest.skip(
        "Set DUCO_SAMPLE_PROFILE to run local sample validation against ignored raw captures",
        allow_module_level=True,
    )

try:
    LOCAL_SAMPLE_FIXTURES = load_local_sample_fixture_set(LOCAL_SAMPLE_PROFILE)
except FileNotFoundError as err:
    pytest.skip(str(err), allow_module_level=True)


@dataclass(frozen=True, slots=True)
class SampleReadCase:
    """Typed read method used for local raw sample validation."""

    request: ReplayRequest
    invoke: Callable[[DucoClient], Awaitable[object]]
    assert_parsed: Callable[[object, object], None]


MINIMAL_LOCAL_SAMPLE_REQUESTS = {
    build_replay_request("GET", "/api"),
    build_replay_request("GET", "/config"),
    build_replay_request("GET", "/config/nodes"),
    build_replay_request("GET", "/config/zones"),
    build_replay_request("GET", "/info", params={"module": "General", "submodule": "Board"}),
    build_replay_request("GET", "/info/nodes"),
    build_replay_request("GET", "/info/zones"),
}


def _assert_api_info(parsed: object, payload: object) -> None:
    api_info = cast(Any, parsed)
    api_payload = cast(dict[str, Any], payload)

    assert api_info.public_api_version == api_payload["PublicApiVersion"]["Val"]
    assert api_info.raw_payload is api_payload


def _assert_board_info(parsed: object, payload: object) -> None:
    board = cast(Any, parsed)
    board_payload = cast(dict[str, Any], payload)["General"]["Board"]

    assert board.public_api_version == board_payload["PublicApiVersion"]["Val"]
    assert board.box_name == board_payload["BoxName"]["Val"]
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


def _assert_nodes(parsed: object, payload: object) -> None:
    nodes = cast(list[Any], parsed)
    nodes_payload = cast(dict[str, Any], payload)["Nodes"]

    assert len(nodes) == len(nodes_payload)

    for node, node_payload in zip(nodes, nodes_payload, strict=True):
        assert node.node_id == node_payload["Node"]
        assert node.raw_payload is node_payload


def _assert_zones_config(parsed: object, payload: object) -> None:
    zones = cast(ConfigZonesOverview, parsed)
    zones_payload = cast(dict[str, Any], payload)["Zones"]

    assert zones.raw_payload is payload
    assert len(zones.zones) == len(zones_payload)


def _assert_zones_info(parsed: object, payload: object) -> None:
    zones = cast(InfoZonesOverview, parsed)
    zones_payload = cast(dict[str, Any], payload)["Zones"]

    assert zones.raw_payload is payload
    assert len(zones.zones) == len(zones_payload)


SAMPLE_READ_CASES = (
    SampleReadCase(
        request=build_replay_request("GET", "/api"),
        invoke=lambda client: client.async_get_api_info(),
        assert_parsed=_assert_api_info,
    ),
    SampleReadCase(
        request=build_replay_request(
            "GET",
            "/info",
            params={"module": "General", "submodule": "Board"},
        ),
        invoke=lambda client: client.async_get_board_info(),
        assert_parsed=_assert_board_info,
    ),
    SampleReadCase(
        request=build_replay_request("GET", "/config"),
        invoke=lambda client: client.async_get_config(),
        assert_parsed=_assert_config,
    ),
    SampleReadCase(
        request=build_replay_request("GET", "/config/nodes"),
        invoke=lambda client: client.async_get_node_configs(),
        assert_parsed=_assert_node_configs,
    ),
    SampleReadCase(
        request=build_replay_request("GET", "/config/zones"),
        invoke=lambda client: client.async_get_zones_config(),
        assert_parsed=_assert_zones_config,
    ),
    SampleReadCase(
        request=build_replay_request("GET", "/info/nodes"),
        invoke=lambda client: client.async_get_nodes(),
        assert_parsed=_assert_nodes,
    ),
    SampleReadCase(
        request=build_replay_request("GET", "/info/zones"),
        invoke=lambda client: client.async_get_zones_info(),
        assert_parsed=_assert_zones_info,
    ),
)


def test_local_sample_profile_covers_minimal_requests() -> None:
    """The configured local sample profile should expose the minimal baseline."""
    assert MINIMAL_LOCAL_SAMPLE_REQUESTS <= set(LOCAL_SAMPLE_FIXTURES)


@pytest.mark.parametrize(
    "case",
    SAMPLE_READ_CASES,
    ids=[f"{case.request.method}-{case.request.path}" for case in SAMPLE_READ_CASES],
)
async def test_local_sample_fixture_parses_through_typed_client(case: SampleReadCase) -> None:
    """Configured local sample fixtures should parse through the selected readers."""
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
            return LOCAL_SAMPLE_FIXTURES[request].payload

        client._request_json = _request_json
        parsed = await case.invoke(client)

    assert requested == [case.request]
    case.assert_parsed(parsed, LOCAL_SAMPLE_FIXTURES[case.request].payload)