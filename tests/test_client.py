"""Tests for the HTTP-only Duco connectivity client."""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, assert_type, cast
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from duco_connectivity import (
    ActionEnumValue,
    ActionItem,
    ActionName,
    ActionResultStatus,
    ActionValueType,
    BoardName,
    BypassSupplyTemperatureTarget,
    Config,
    ConfigAutoRebootComm,
    ConfigGeneral,
    ConfigGeneralSubmoduleSelector,
    ConfigGroup,
    ConfigHeatRecovery,
    ConfigHeatRecoveryBypass,
    ConfigHeatRecoverySubmoduleSelector,
    ConfigLan,
    ConfigModbus,
    ConfigModuleSelector,
    ConfigNode,
    ConfigNodeOverview,
    ConfigNodeStruct,
    ConfigSection,
    ConfigTime,
    ConfigValue,
    ConfigValueOptions,
    ConfigValueString,
    ConfigZone,
    ConfigZonesOverview,
    ConfigZoneWithGroupStruct,
    DeviceGroupConfigSubmoduleSelector,
    DiagComponent,
    DiagInfo,
    DucoClient,
    DucoConnectionError,
    DucoError,
    DucoResponseError,
    DucoSerialNumber,
    DucoUnsupportedCapabilityError,
    DucoVersion,
    DucoWriteLimitError,
    HostName,
    InfoGeneralSubmoduleSelector,
    InfoGroup,
    InfoModuleSelector,
    InfoZone,
    InfoZoneGroup,
    InfoZonesOverview,
    IpAddress,
    KnownBoardName,
    KnownLanMode,
    LanMode,
    MacAddress,
    NetworkType,
    NodeActionItemList,
    NodeAirQualityIndex,
    NodeAssociationId,
    NodeCo2Ppm,
    NodeIdentify,
    NodeInfoModuleSelector,
    NodeListActionItemList,
    NodeMotorDeviceType,
    NodeMotorPosition,
    NodeMotorRequest,
    NodeName,
    NodeOverview,
    NodeParentId,
    NodeRelativeHumidity,
    NodeSubtype,
    NodeTemperature,
    NodeType,
    PatchConfig,
    PatchConfigAutoRebootComm,
    PatchConfigGeneral,
    PatchConfigHeatRecovery,
    PatchConfigHeatRecoveryBypass,
    PatchConfigLan,
    PatchConfigModbus,
    PatchConfigModel,
    PatchConfigNodeStruct,
    PatchConfigNodeValue,
    PatchConfigTime,
    PatchConfigValue,
    PatchConfigZoneDeviceGroupConfig,
    PatchConfigZoneGeneral,
    PatchConfigZoneStruct,
    VentilationFlowLevelTarget,
    VentilationMode,
    VentilationState,
    VentilationTemperatureInfo,
    VentilationTimeEnd,
    VentilationTimeRemaining,
    ZoneModuleSelector,
)


def _response(
    *,
    status: int = 200,
    json_payload: object | None = None,
    json_side_effect: Exception | None = None,
    text_payload: str = "",
) -> MagicMock:
    """Create a mock aiohttp response."""
    response = MagicMock()
    response.status = status
    response.text = AsyncMock(return_value=text_payload)
    if json_side_effect is not None:
        response.json = AsyncMock(side_effect=json_side_effect)
    else:
        response.json = AsyncMock(return_value=json_payload)
    return response


def _request_context(response: MagicMock) -> MagicMock:
    """Create a mock aiohttp request context manager."""
    request_context = MagicMock()
    request_context.__aenter__ = AsyncMock(return_value=response)
    request_context.__aexit__ = AsyncMock(return_value=False)
    return request_context


def _request(response: MagicMock) -> MagicMock:
    """Create a mock request callable returning a request context manager."""
    return MagicMock(return_value=_request_context(response))


def _build_async_wrapper(module_name: str, source: str) -> object:
    """Create an async wrapper function in a custom module namespace."""
    namespace = {"__name__": module_name}
    exec(source, namespace)
    return namespace["external_wrapper"]


NODE_CONFIG_MALFORMED_PAYLOADS: list[tuple[object, str]] = [
    ([], "Expected object payload from /config/nodes, got list"),
    ({}, "Expected list Nodes in /config/nodes response"),
    ({"Nodes": {}}, "Expected list Nodes in /config/nodes response"),
    (
        {"Nodes": [False]},
        "Expected object item at index 0 in /config/nodes response, got bool",
    ),
    ({"Nodes": [{}]}, "Expected integer Node in /config/nodes item at index 0"),
    (
        {"Nodes": [{"Node": "1"}]},
        "Expected integer Node in /config/nodes item at index 0, got str",
    ),
    (
        {"Nodes": [{"Node": 1, "Name": "DucoBox"}]},
        "Expected object for node config value /config/nodes item at index 0.Name, got str",
    ),
    (
        {"Nodes": [{"Node": 1, "Name": {}}]},
        "Expected Val in node config value /config/nodes item at index 0.Name",
    ),
    (
        {"Nodes": [{"Node": 1, "Name": {"Val": 1}}]},
        "Expected string Val for node config value /config/nodes item at index 0.Name, got int",
    ),
]

ZONES_CONFIG_MALFORMED_PAYLOADS: list[tuple[object, str]] = [
    ([], "Expected object payload from /config/zones, got list"),
    ({}, "Expected list Zones in /config/zones response"),
    ({"Zones": {}}, "Expected list Zones in /config/zones response"),
    (
        {"Zones": [False]},
        "Expected object payload from /config/zones item at index 0, got bool",
    ),
    ({"Zones": [{}]}, "Expected integer Zone in /config/zones item at index 0"),
    (
        {"Zones": [{"Zone": "1"}]},
        "Expected integer Zone in /config/zones item at index 0, got str",
    ),
    (
        {"Zones": [{"Zone": 1, "Groups": {}}]},
        "Expected list Groups in /config/zones item at index 0",
    ),
    (
        {"Zones": [{"Zone": 1, "Groups": [{}]}]},
        "Expected integer Group in /config/zones item at index 0.Groups item at index 0",
    ),
    (
        {"Zones": [{"Zone": 1, "DeviceGroupConfig": "General"}]},
        "Expected object DeviceGroupConfig in /config/zones item at index 0",
    ),
    (
        {"Zones": [{"Zone": 1, "DeviceGroupConfig": {"General": 1}}]},
        "Expected object General in /config/zones item at index 0.DeviceGroupConfig",
    ),
    (
        {"Zones": [{"Zone": 1, "DeviceGroupConfig": {"General": {"Name": "Ground floor"}}}]},
        (
            "Expected object for zone config value "
            "/config/zones item at index 0.DeviceGroupConfig.General.Name, got str"
        ),
    ),
    (
        {"Zones": [{"Zone": 1, "DeviceGroupConfig": {"General": {"Name": {}}}}]},
        (
            "Expected Val in zone config value "
            "/config/zones item at index 0.DeviceGroupConfig.General.Name"
        ),
    ),
    (
        {"Zones": [{"Zone": 1, "DeviceGroupConfig": {"General": {"Name": {"Val": 1}}}}]},
        (
            "Expected string Val for zone config value "
            "/config/zones item at index 0.DeviceGroupConfig.General.Name, got int"
        ),
    ),
]

ZONE_CONFIG_MALFORMED_PAYLOADS: list[tuple[object, str]] = [
    (False, "Expected object payload from /config/zones/1, got bool"),
    ({}, "Expected integer Zone in /config/zones/1"),
    (
        {"Zone": "1"},
        "Expected integer Zone in /config/zones/1, got str",
    ),
    (
        {"Zone": 1, "Groups": {}},
        "Expected list Groups in /config/zones/1",
    ),
    (
        {"Zone": 1, "Groups": [{}]},
        "Expected integer Group in /config/zones/1.Groups item at index 0",
    ),
    (
        {"Zone": 1, "DeviceGroupConfig": "General"},
        "Expected object DeviceGroupConfig in /config/zones/1",
    ),
    (
        {"Zone": 1, "DeviceGroupConfig": {"General": 1}},
        "Expected object General in /config/zones/1.DeviceGroupConfig",
    ),
    (
        {"Zone": 1, "DeviceGroupConfig": {"General": {"Name": "Ground floor"}}},
        (
            "Expected object for zone config value "
            "/config/zones/1.DeviceGroupConfig.General.Name, got str"
        ),
    ),
    (
        {"Zone": 1, "DeviceGroupConfig": {"General": {"Name": {}}}},
        "Expected Val in zone config value /config/zones/1.DeviceGroupConfig.General.Name",
    ),
    (
        {"Zone": 1, "DeviceGroupConfig": {"General": {"Name": {"Val": 1}}}},
        (
            "Expected string Val for zone config value "
            "/config/zones/1.DeviceGroupConfig.General.Name, got int"
        ),
    ),
]

ACTION_DISCOVERY_MALFORMED_PAYLOADS: list[tuple[object, str]] = [
    (None, "Expected list payload from /action, got NoneType"),
    ({}, "Expected list payload from /action, got dict"),
    (
        ["SetIdentify"],
        "Expected object /action item at index 0 in /action response, got str",
    ),
    ([{}], "Expected Action in /action item at index 0"),
    (
        [{"Action": 1, "ValType": "None"}],
        "Expected string Action in /action item at index 0, got int",
    ),
    (
        [{"Action": "SetIdentify"}],
        "Expected ValType in /action item at index 0",
    ),
    (
        [{"Action": "SetIdentify", "ValType": 1}],
        "Expected string ValType in /action item at index 0, got int",
    ),
    (
        [{"Action": "SetWifiApMode", "ValType": "Enum", "Enum": "On"}],
        "Expected list Enum in /action item at index 0, got str",
    ),
    (
        [{"Action": "SetWifiApMode", "ValType": "Enum", "Enum": [1]}],
        "Expected string Enum value at /action item at index 0.Enum[0], got int",
    ),
]

NODE_ACTION_DISCOVERY_MALFORMED_PAYLOADS: list[tuple[object, str]] = [
    (None, "Expected object payload from /action/nodes, got NoneType"),
    ([], "Expected object payload from /action/nodes, got list"),
    ({}, "Expected Nodes in /action/nodes response"),
    ({"Nodes": {}}, "Expected list Nodes in /action/nodes response, got dict"),
    (
        {"Nodes": [False]},
        "Expected object /action/nodes item at index 0 in /action/nodes response, got bool",
    ),
    ({"Nodes": [{}]}, "Expected Node in /action/nodes item at index 0"),
    (
        {"Nodes": [{"Node": "1"}]},
        "Expected integer Node in /action/nodes item at index 0, got str",
    ),
    (
        {"Nodes": [{"Node": 1, "Actions": {}}]},
        "Expected list Actions in /action/nodes item at index 0, got dict",
    ),
    (
        {"Nodes": [{"Node": 1, "Actions": [False]}]},
        (
            "Expected object /action/nodes item at index 0.Actions item at index 0 "
            "in /action/nodes response, got bool"
        ),
    ),
]

NODE_ACTION_DISCOVERY_FOR_NODE_MALFORMED_PAYLOADS: list[tuple[object, str]] = [
    (None, "Expected object payload from /action/nodes/7, got NoneType"),
    ([], "Expected object payload from /action/nodes/7, got list"),
    ({}, "Expected Node in /action/nodes/7 payload"),
    ({"Node": "7"}, "Expected integer Node in /action/nodes/7 payload, got str"),
    (
        {"Node": 7, "Actions": {}},
        "Expected list Actions in /action/nodes/7 payload, got dict",
    ),
    (
        {"Node": 7, "Actions": [False]},
        (
            "Expected object /action/nodes/7 payload.Actions item at index 0 "
            "in /action/nodes/7 response, got bool"
        ),
    ),
]

ZONES_INFO_MALFORMED_PAYLOADS: list[tuple[object, str]] = [
    ([], "Expected object payload from /info/zones, got list"),
    ({}, "Expected list Zones in /info/zones response"),
    ({"Zones": {}}, "Expected list Zones in /info/zones response"),
    (
        {"Zones": [False]},
        "Expected object /info/zones item at index 0 in /info/zones response, got bool",
    ),
    ({"Zones": [{}]}, "Expected integer Zone in /info/zones item at index 0"),
    (
        {"Zones": [{"Zone": "1"}]},
        "Expected integer Zone in /info/zones item at index 0, got str",
    ),
    (
        {"Zones": [{"Zone": 1, "Groups": {}}]},
        "Expected list Groups in /info/zones item at index 0",
    ),
    (
        {"Zones": [{"Zone": 1, "Groups": [{}]}]},
        "Expected integer Group in /info/zones item at index 0.Groups item at index 0",
    ),
    (
        {"Zones": [{"Zone": 1, "DeviceGroupConfig": {"General": {"Name": 1}}}]},
        "Expected string Name in /info/zones item at index 0.DeviceGroupConfig.General, got int",
    ),
    (
        {
            "Zones": [
                {
                    "Zone": 1,
                    "Groups": [
                        {
                            "Group": 1,
                            "DeviceGroupConfig": {"General": {"Nodes": [7, "8"]}},
                        }
                    ],
                }
            ]
        },
        (
            "Expected integer node ID at /info/zones item at index 0.Groups item at "
            "index 0.DeviceGroupConfig.General.Nodes\\[1\\], got str"
        ),
    ),
]

ZONE_INFO_MALFORMED_PAYLOADS: list[tuple[object, str]] = [
    ([], "Expected object payload from /info/zones/1, got list"),
    ({}, "Expected integer Zone in /info/zones/1"),
    ({"Zone": "1"}, "Expected integer Zone in /info/zones/1, got str"),
    ({"Zone": 1, "Groups": {}}, "Expected list Groups in /info/zones/1"),
    (
        {"Zone": 1, "Groups": [False]},
        "Expected object /info/zones/1.Groups item at index 0, got bool",
    ),
    (
        {"Zone": 1, "DeviceGroupConfig": {"General": {"Name": 1}}},
        "Expected string Name in /info/zones/1.DeviceGroupConfig.General, got int",
    ),
    (
        {
            "Zone": 1,
            "Groups": [
                {
                    "Group": 1,
                    "DeviceGroupConfig": {"General": {"Nodes": [7, "8"]}},
                }
            ],
        },
        (
            "Expected integer node ID at /info/zones/1.Groups item at index 0"
            ".DeviceGroupConfig.General.Nodes\\[1\\], got str"
        ),
    ),
]

ZONE_GROUP_INFO_MALFORMED_PAYLOADS: list[tuple[object, str]] = [
    ([], "Expected object payload from /info/zones/1/groups/2, got list"),
    ({}, "Expected integer Zone in /info/zones/1/groups/2"),
    ({"Zone": "1"}, "Expected integer Zone in /info/zones/1/groups/2, got str"),
    ({"Zone": 1}, "Expected integer Group in /info/zones/1/groups/2"),
    (
        {"Zone": 1, "Group": "2"},
        "Expected integer Group in /info/zones/1/groups/2, got str",
    ),
    (
        {
            "Zone": 1,
            "Group": 2,
            "DeviceGroupConfig": {"General": {"Nodes": [11, "12"]}},
        },
        (
            "Expected integer node ID at /info/zones/1/groups/2.DeviceGroupConfig"
            ".General.Nodes\\[1\\], got str"
        ),
    ),
]


async def test_https_is_rejected() -> None:
    """HTTPS hosts should be rejected during client construction."""
    async with aiohttp.ClientSession() as session:
        with pytest.raises(ValueError, match="HTTPS"):
            DucoClient(session=session, host="https://192.0.2.94")


async def test_base_url_defaults_to_http() -> None:
    """Test that a bare host is normalized to an HTTP base URL."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        assert client.base_url == "http://192.0.2.94"


async def test_base_url_uses_embedded_port_from_host() -> None:
    """Hosts with an embedded port should preserve that port in the base URL."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="http://192.0.2.94:8080")
        assert client.base_url == "http://192.0.2.94:8080"


async def test_bracketed_ipv6_host_is_accepted() -> None:
    """Bracketed IPv6 hosts should be accepted and normalized."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="[fe80::1]")
        assert client.base_url == "http://[fe80::1]"


async def test_uppercase_http_scheme_is_accepted() -> None:
    """HTTP hosts should be accepted regardless of scheme casing."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="HTTP://192.0.2.94:8080")
        assert client.base_url == "http://192.0.2.94:8080"


async def test_conflicting_port_sources_are_rejected() -> None:
    """The client should reject a separate port when the host already includes one."""
    async with aiohttp.ClientSession() as session:
        with pytest.raises(ValueError, match="Port specified both"):
            DucoClient(session=session, host="192.0.2.94:8080", port=8081)


async def test_userinfo_in_host_is_rejected() -> None:
    """The unauthenticated client should reject credentials embedded in the host value."""
    async with aiohttp.ClientSession() as session:
        with pytest.raises(ValueError, match="must not include user credentials"):
            DucoClient(session=session, host="user:pass@192.0.2.94")


async def test_invalid_embedded_port_is_rejected() -> None:
    """Malformed embedded ports should raise a consistent client ValueError."""
    async with aiohttp.ClientSession() as session:
        with pytest.raises(ValueError, match="Invalid port in host value"):
            DucoClient(session=session, host="192.0.2.94:abc")


async def test_unbracketed_ipv6_host_is_rejected() -> None:
    """Bare IPv6 hosts should require brackets to avoid ambiguous parsing."""
    async with aiohttp.ClientSession() as session:
        with pytest.raises(ValueError, match="Unbracketed IPv6 host values"):
            DucoClient(session=session, host="fe80::1")


async def test_negative_port_argument_is_rejected() -> None:
    """Explicit negative ports should be rejected during client construction."""
    async with aiohttp.ClientSession() as session:
        with pytest.raises(ValueError, match="Invalid port argument"):
            DucoClient(session=session, host="192.0.2.94", port=-1)


async def test_out_of_range_port_argument_is_rejected() -> None:
    """Explicit ports above 65535 should be rejected during client construction."""
    async with aiohttp.ClientSession() as session:
        with pytest.raises(ValueError, match="Invalid port argument"):
            DucoClient(session=session, host="192.0.2.94", port=99999)


async def test_api_info_is_parsed(api_info_full_data: dict[str, object]) -> None:
    """Test that the API info model follows the public API payload."""
    mock_response = _response(json_payload=api_info_full_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            api_info = await client.async_get_api_info()

    assert isinstance(api_info.public_api_version, DucoVersion)
    assert api_info.public_api_version == "2.6"
    assert api_info.public_api_version.components == (2, 6)
    assert api_info.reported_api_version == "MOCKAPI 2.6.0"
    assert len(api_info.endpoints) == 2
    assert api_info.endpoints[1].url == "/info"
    assert api_info.endpoints[1].query_parameters == [
        "module",
        "submodule",
        "parameter",
    ]
    assert api_info.raw_payload is api_info_full_data
    assert api_info.endpoints[0].raw_payload is api_info_full_data["ApiInfo"][0]


async def test_request_logging_includes_method_path_and_status(
    caplog: pytest.LogCaptureFixture,
    api_info_full_data: dict[str, object],
) -> None:
    """Requests should emit debug logs for the request and response."""
    mock_response = _response(json_payload=api_info_full_data)

    async with aiohttp.ClientSession() as session:
        with caplog.at_level(logging.DEBUG, logger="duco_connectivity.client"):
            client = DucoClient(session=session, host="192.0.2.94")
            with patch.object(session, "request", _request(mock_response)):
                await client.async_get_api_info()

    assert "Initialized DucoClient for http://192.0.2.94" in caplog.text
    assert "Using HTTP-only duco_connectivity transport for http://192.0.2.94." in caplog.text
    assert "Requesting GET http://192.0.2.94/api" in caplog.text
    assert "Received response 200 for GET http://192.0.2.94/api" in caplog.text


async def test_get_raw_without_query_params_returns_raw_payload() -> None:
    """The generic raw reader should expose unmapped GET payloads unchanged."""
    mock_response = _response(json_payload={"Nodes": [{"Node": {"Val": 7}}]})

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            payload = await client.async_get_raw("/nodes")

    assert payload == {"Nodes": [{"Node": {"Val": 7}}]}
    assert request_mock.call_args.args == ("GET", "http://192.0.2.94/nodes")
    assert "params" not in request_mock.call_args.kwargs


async def test_get_raw_with_query_params_forwards_query_params() -> None:
    """The generic raw reader should forward caller-supplied query params unchanged."""
    mock_response = _response(json_payload={"Temperature": {"Val": 21}})

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            payload = await client.async_get_raw(
                "/info/nodes/7",
                params={"module": "Sensor", "parameter": "Temperature"},
            )

    assert payload == {"Temperature": {"Val": 21}}
    assert request_mock.call_args.args == ("GET", "http://192.0.2.94/info/nodes/7")
    assert request_mock.call_args.kwargs["params"] == {
        "module": "Sensor",
        "parameter": "Temperature",
    }


@pytest.mark.parametrize(
    ("path", "message"),
    [
        ("nodes", "async_get_raw path must start with /"),
        ("http://192.0.2.94/nodes", "async_get_raw path must be API-relative, not a full URL"),
        (
            "/nodes?module=General",
            "async_get_raw path must not include a query string or fragment; use params instead",
        ),
        (
            "/nodes#fragment",
            "async_get_raw path must not include a query string or fragment; use params instead",
        ),
    ],
)
async def test_get_raw_rejects_invalid_public_paths(path: str, message: str) -> None:
    """The generic raw reader should reject non-relative or ambiguous paths."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")

        with pytest.raises(ValueError, match=re.escape(message)):
            await client.async_get_raw(path)


async def test_get_raw_api_error_raises_duco_error() -> None:
    """HTTP errors from the generic raw reader should surface as DucoError."""
    mock_response = _response(status=404, text_payload="missing endpoint")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match="Unexpected response 404 for /unmapped: missing endpoint",
            ),
        ):
            await client.async_get_raw("/unmapped")


async def test_get_raw_connection_error_raises_duco_connection_error() -> None:
    """Transport failures from the generic raw reader should surface as connection errors."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(
                session,
                "request",
                MagicMock(side_effect=aiohttp.ClientError("boom")),
            ),
            pytest.raises(DucoConnectionError, match="Could not reach Duco device"),
        ):
            await client.async_get_raw("/nodes")


async def test_get_info_without_query_params_returns_raw_payload(
    generic_info_all_data: dict[str, object],
) -> None:
    """The generic info reader should expose the raw payload unchanged."""
    mock_response = _response(json_payload=generic_info_all_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            payload = await client.async_get_info()

    assert payload == generic_info_all_data
    assert "params" not in request_mock.call_args.kwargs


async def test_get_info_with_module_forwards_query_params(
    generic_info_general_data: dict[str, object],
) -> None:
    """A module query should be forwarded to the generic info endpoint."""
    mock_response = _response(json_payload=generic_info_general_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            payload = await client.async_get_info(module="General")

    assert payload == generic_info_general_data
    assert request_mock.call_args.kwargs["params"] == {"module": "General"}


async def test_get_info_with_module_and_submodule_forwards_query_params(
    generic_info_board_data: dict[str, object],
) -> None:
    """Module and submodule queries should be forwarded unchanged."""
    mock_response = _response(json_payload=generic_info_board_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            payload = await client.async_get_info(
                module="General",
                submodule="Board",
            )

    assert payload == generic_info_board_data
    assert request_mock.call_args.kwargs["params"] == {
        "module": "General",
        "submodule": "Board",
    }


async def test_get_info_with_module_submodule_and_parameter_forwards_query_params(
    generic_info_board_data: dict[str, object],
) -> None:
    """All supported info query parameters should be forwarded unchanged."""
    mock_response = _response(json_payload=generic_info_board_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            payload = await client.async_get_info(
                module="General",
                submodule="Board",
                parameter="PublicApiVersion",
            )

    assert payload == generic_info_board_data
    assert request_mock.call_args.kwargs["params"] == {
        "module": "General",
        "submodule": "Board",
        "parameter": "PublicApiVersion",
    }


async def test_get_info_accepts_selector_enums(
    generic_info_board_data: dict[str, object],
) -> None:
    """Known info selector enums should serialize to the documented raw query values."""
    mock_response = _response(json_payload=generic_info_board_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            await client.async_get_info(
                module=InfoModuleSelector.GENERAL,
                submodule=InfoGeneralSubmoduleSelector.BOARD,
                parameter="PublicApiVersion",
            )

    assert request_mock.call_args.kwargs["params"] == {
        "module": "General",
        "submodule": "Board",
        "parameter": "PublicApiVersion",
    }


async def test_get_info_api_error_raises_duco_error() -> None:
    """HTTP errors from the generic info endpoint should surface as DucoError."""
    mock_response = _response(status=400, text_payload="unsupported query")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match="Unexpected response 400 for /info: unsupported query",
            ),
        ):
            await client.async_get_info(module="General")


async def test_get_info_connection_error_raises_duco_connection_error() -> None:
    """Transport failures from the generic info endpoint should surface as connection errors."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(
                session,
                "request",
                MagicMock(side_effect=aiohttp.ClientError("boom")),
            ),
            pytest.raises(DucoConnectionError, match="Could not reach Duco device"),
        ):
            await client.async_get_info(module="General")


async def test_get_config_without_query_params_returns_typed_payload(
    config_data: dict[str, object],
) -> None:
    """The generic config reader should expose a typed config tree."""
    mock_response = _response(json_payload=config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            payload = await client.async_get_config()

    assert isinstance(payload, Config)
    assert "params" not in request_mock.call_args.kwargs

    general = payload.sections["General"]
    assert isinstance(general, ConfigSection)

    time_config = general.entries["Time"]
    assert isinstance(time_config, ConfigSection)

    time_zone = time_config.entries["TimeZone"]
    assert isinstance(time_zone, ConfigValue)
    assert time_zone.value == 1
    assert time_zone.minimum == -12
    assert time_zone.increment == 1
    assert time_zone.maximum == 12

    lan_config = general.entries["Lan"]
    assert isinstance(lan_config, ConfigSection)

    mode = lan_config.entries["Mode"]
    assert isinstance(mode, ConfigValueOptions)
    assert isinstance(mode, ConfigValue)
    assert mode.options == (1, 2, 4)

    static_ip = lan_config.entries["StaticIp"]
    assert isinstance(static_ip, ConfigValueString)
    assert static_ip.value == "192.0.2.94"
    assert payload.general == ConfigGeneral(
        time=ConfigTime(
            time_zone=ConfigValue(value=1, minimum=-12, increment=1, maximum=12),
            dst=ConfigValue(value=1, minimum=0, increment=1, maximum=1),
        ),
        modbus=ConfigModbus(
            addr=ConfigValue(value=10, minimum=1, increment=1, maximum=247),
            offset=ConfigValue(value=0, minimum=0, increment=1, maximum=255),
        ),
        lan=ConfigLan(
            mode=ConfigValueOptions(value=1, options=(1, 2, 4)),
            dhcp=ConfigValue(value=1, minimum=0, increment=1, maximum=1),
            static_ip=ConfigValueString(value="192.0.2.94"),
            static_net_mask=ConfigValueString(value="255.255.255.0"),
            static_default_gateway=ConfigValueString(value="192.0.2.1"),
            static_dns=ConfigValueString(value="192.0.2.1"),
            wifi_client_ssid=ConfigValueString(value="duco-test-net"),
            wifi_client_key=ConfigValueString(value="duco-secret"),
        ),
        auto_reboot_comm=ConfigAutoRebootComm(
            period=ConfigValue(value=7, minimum=0, increment=1, maximum=30),
            time=ConfigValue(value=120, minimum=0, increment=30, maximum=1440),
        ),
    )
    assert payload.heat_recovery == ConfigHeatRecovery(
        bypass=ConfigHeatRecoveryBypass(
            temp_sup_tgt_zone_1=ConfigValue(value=180, minimum=120, increment=5, maximum=220),
            temp_sup_tgt_zone_2=ConfigValue(value=185, minimum=120, increment=5, maximum=220),
        )
    )
    assert payload.raw_payload is config_data
    assert general.raw_payload is config_data["General"]
    assert time_zone.raw_payload is config_data["General"]["Time"]["TimeZone"]


async def test_get_config_parses_option_lists_as_tuples() -> None:
    """Integer option lists should be preserved in the typed config value."""
    mock_response = _response(
        json_payload={
            "General": {
                "Lan": {
                    "Mode": {
                        "Val": 1,
                        "Options": [1, 2, 4],
                    }
                }
            }
        }
    )

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            payload = await client.async_get_config()

    mode = payload.sections["General"].entries["Lan"]
    assert isinstance(mode, ConfigSection)
    mode_value = mode.entries["Mode"]
    assert isinstance(mode_value, ConfigValueOptions)
    assert mode_value.options == (1, 2, 4)
    assert mode_value.raw_payload == {"Val": 1, "Options": [1, 2, 4]}


async def test_get_config_preserves_unmapped_leaf_metadata() -> None:
    """Typed config leaves should retain the original API object for forward compatibility."""
    payload: dict[str, object] = {
        "General": {
            "Lan": {
                "Mode": {
                    "Val": 1,
                    "Options": [1, 2, 4],
                    "Unit": "profile",
                }
            }
        }
    }
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            config = await client.async_get_config()

    mode = config.sections["General"].entries["Lan"]
    assert isinstance(mode, ConfigSection)
    mode_value = mode.entries["Mode"]
    assert isinstance(mode_value, ConfigValueOptions)
    assert mode_value.raw_payload["Unit"] == "profile"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {"General": {"Lan": {"StaticIp": {"Val": 1}}}},
            "Expected string config value General.Lan.StaticIp, got ConfigValue",
        ),
        (
            {"General": {"Time": {"TimeZone": {"Val": "1"}}}},
            "Expected integer config value General.Time.TimeZone, got ConfigValueString",
        ),
    ],
)
async def test_get_config_rejects_mismatched_stable_typed_branch_payloads(
    payload: dict[str, object],
    message: str,
) -> None:
    """Stable typed config families should reject payloads that change the documented value type."""
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoError, match=message),
        ):
            await client.async_get_config()


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {"General": {"Lan": {"Dhcp": {"Val": False}}}},
            "Unsupported config value type bool for General.Lan.Dhcp",
        ),
        (
            {"General": {"Time": {"TimeZone": {"Val": 1, "Min": False}}}},
            "Expected integer Min for config entry General.Time.TimeZone",
        ),
        (
            {"General": {"Lan": {"Mode": {"Val": 1, "Options": [1, False]}}}},
            "Expected integer option list for config entry General.Lan.Mode",
        ),
        (
            {
                "General": {
                    "Lan": {"Mode": {"Val": 1, "Min": 1, "Inc": 1, "Max": 4, "Options": [1, 2, 4]}}
                }
            },
            "Config entry General.Lan.Mode cannot combine range metadata with Options",
        ),
    ],
)
async def test_get_config_rejects_invalid_integer_payloads(
    payload: dict[str, object],
    message: str,
) -> None:
    """Invalid integer-like config payloads should raise DucoError."""
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoError, match=message),
        ):
            await client.async_get_config()


def test_generic_config_models_cover_node_and_patch_shapes() -> None:
    """Generic config models should cover future read and write payload shapes."""
    name = ConfigValueString(value="Kitchen valve")
    node_struct = ConfigNodeStruct(name=name)
    node = ConfigNode(node_id=7, name=name)
    overview = ConfigNodeOverview(nodes=[node])
    zone_group_struct = ConfigZoneWithGroupStruct(name=name, groups=[ConfigGroup(group_id=2)])
    patch_value = PatchConfigValue(value=2)
    patch_node_value = PatchConfigNodeValue(value="Boost")
    patch_zone_struct = PatchConfigZoneStruct(
        device_group_config=PatchConfigZoneDeviceGroupConfig(
            general=PatchConfigZoneGeneral(name=PatchConfigValue(value="Ground floor"))
        )
    )

    assert node_struct.name is name
    assert node.node_id == 7
    assert node.name is name
    assert overview.nodes == [node]
    assert zone_group_struct.name is name
    assert zone_group_struct.groups == [ConfigGroup(group_id=2)]
    assert patch_value.value == 2
    assert patch_node_value.value == "Boost"
    assert patch_zone_struct.device_group_config is not None
    assert patch_zone_struct.device_group_config.general is not None
    assert patch_zone_struct.device_group_config.general.name == PatchConfigValue(
        value="Ground floor"
    )
    assert not isinstance(patch_zone_struct.device_group_config.general, PatchConfigModel)
    assert not isinstance(patch_zone_struct.device_group_config, PatchConfigModel)


async def test_get_config_with_module_forwards_query_params(
    config_data: dict[str, object],
) -> None:
    """A module query should be forwarded to the generic config endpoint."""
    mock_response = _response(json_payload=config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            payload = await client.async_get_config(module="General")

    assert isinstance(payload, Config)
    assert request_mock.call_args.kwargs["params"] == {"module": "General"}


async def test_get_config_with_module_and_submodule_forwards_query_params(
    config_data: dict[str, object],
) -> None:
    """Module and submodule queries should be forwarded unchanged."""
    mock_response = _response(json_payload=config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            payload = await client.async_get_config(
                module="General",
                submodule="Lan",
            )

    assert isinstance(payload, Config)
    assert request_mock.call_args.kwargs["params"] == {
        "module": "General",
        "submodule": "Lan",
    }


async def test_get_config_with_module_submodule_and_parameter_forwards_query_params(
    config_data: dict[str, object],
) -> None:
    """All supported config query parameters should be forwarded unchanged."""
    mock_response = _response(json_payload=config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            payload = await client.async_get_config(
                module="General",
                submodule="Lan",
                parameter="StaticIp",
            )

    assert isinstance(payload, Config)
    assert request_mock.call_args.kwargs["params"] == {
        "module": "General",
        "submodule": "Lan",
        "parameter": "StaticIp",
    }


async def test_get_config_accepts_selector_enums(
    config_data: dict[str, object],
) -> None:
    """Known config selector enums should serialize to the documented raw query values."""
    mock_response = _response(json_payload=config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            await client.async_get_config(
                module=ConfigModuleSelector.HEAT_RECOVERY,
                submodule=ConfigHeatRecoverySubmoduleSelector.BYPASS,
                parameter="TempSupTgtZone1",
            )

    assert request_mock.call_args.kwargs["params"] == {
        "module": "HeatRecovery",
        "submodule": "Bypass",
        "parameter": "TempSupTgtZone1",
    }


async def test_get_config_api_error_raises_duco_error() -> None:
    """HTTP errors from the generic config endpoint should surface as DucoError."""
    mock_response = _response(status=400, text_payload="unsupported query")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match="Unexpected response 400 for /config: unsupported query",
            ),
        ):
            await client.async_get_config(module="General")


async def test_get_config_connection_error_raises_duco_connection_error() -> None:
    """Transport failures from the generic config endpoint should surface as connection errors."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(
                session,
                "request",
                MagicMock(side_effect=aiohttp.ClientError("boom")),
            ),
            pytest.raises(DucoConnectionError, match="Could not reach Duco device"),
        ):
            await client.async_get_config(module="General")


async def test_set_config_returns_typed_payload_and_compact_json_body() -> None:
    """Generic config writes should return a typed config tree and compact JSON."""
    mock_response = _response(
        json_payload={
            "General": {
                "Lan": {
                    "Mode": {
                        "Val": 2,
                        "Options": [1, 2, 4],
                    }
                }
            }
        }
    )

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            payload = await client.async_set_config(
                {"General": {"Lan": {"Mode": PatchConfigValue(value=2)}}},
                module="General",
                submodule="Lan",
                parameter="Mode",
            )

    assert isinstance(payload, Config)
    mode = payload.sections["General"].entries["Lan"]
    assert isinstance(mode, ConfigSection)
    mode_value = mode.entries["Mode"]
    assert isinstance(mode_value, ConfigValueOptions)
    assert mode_value.value == 2
    _, kwargs = request.call_args
    assert kwargs["params"] == {
        "module": "General",
        "submodule": "Lan",
        "parameter": "Mode",
    }
    assert kwargs["data"] == b'{"General":{"Lan":{"Mode":{"Val":2}}}}'
    assert kwargs["headers"] == {"Content-Type": "application/json"}


async def test_set_config_accepts_api_shaped_leaf_payloads(
    config_data: dict[str, object],
) -> None:
    """Generic config writes should also accept pre-wrapped API-shaped leaf payloads."""
    mock_response = _response(json_payload=config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            payload = await client.async_set_config({"General": {"Time": {"TimeZone": {"Val": 1}}}})

    assert isinstance(payload, Config)
    _, kwargs = request.call_args
    assert "params" not in kwargs
    assert kwargs["data"] == b'{"General":{"Time":{"TimeZone":{"Val":1}}}}'


async def test_set_config_accepts_typed_patch_model_payloads(
    config_data: dict[str, object],
) -> None:
    """Generic config writes should serialize typed patch model families."""
    mock_response = _response(json_payload=config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            payload = await client.async_set_config(
                PatchConfig(
                    general=PatchConfigGeneral(
                        time=PatchConfigTime(time_zone=PatchConfigValue(value=1)),
                        modbus=PatchConfigModbus(addr=PatchConfigValue(value=10)),
                        lan=PatchConfigLan(
                            mode=PatchConfigValue(value=2),
                            static_ip=PatchConfigValue(value="192.0.2.94"),
                        ),
                        auto_reboot_comm=PatchConfigAutoRebootComm(
                            period=PatchConfigValue(value=7)
                        ),
                    ),
                    heat_recovery=PatchConfigHeatRecovery(
                        bypass=PatchConfigHeatRecoveryBypass(
                            temp_sup_tgt_zone_1=PatchConfigValue(value=180)
                        )
                    ),
                )
            )

    assert isinstance(payload, Config)
    _, kwargs = request.call_args
    assert kwargs["data"] == (
        b'{"General":{"Time":{"TimeZone":{"Val":1}},"Modbus":{"Addr":{"Val":10}},'
        b'"Lan":{"Mode":{"Val":2},"StaticIp":{"Val":"192.0.2.94"}},'
        b'"AutoRebootComm":{"Period":{"Val":7}}},'
        b'"HeatRecovery":{"Bypass":{"TempSupTgtZone1":{"Val":180}}}}'
    )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {"General": {"Time": {"TimeZone": 1}}},
            "Unsupported patch config payload type int for config.General.Time.TimeZone",
        ),
        (
            {"General": {"Time": {"TimeZone": {"Val": False}}}},
            "Unsupported patch config value type bool for config.General.Time.TimeZone",
        ),
        (
            {"General": {1: {"Val": 2}}},
            "Expected string key for config.General, got int",
        ),
        (
            {"General": {"Time": {"TimeZone": {"Val": 1, "Min": 0}}}},
            "Patch config leaf config.General.Time.TimeZone may only contain Val",
        ),
    ],
)
async def test_set_config_rejects_invalid_patch_payloads(
    payload: dict[str, object],
    message: str,
) -> None:
    """Invalid generic config patch payloads should fail before the request is sent."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with pytest.raises(ValueError, match=message):
            await client.async_set_config(payload)


async def test_set_config_rejects_non_dataclass_patch_model() -> None:
    """Public patch model subclasses should fail clearly when they are not dataclasses."""

    class BrokenPatch(PatchConfigModel):
        pass

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with pytest.raises(
            ValueError,
            match="Expected dataclass patch payload for config, got BrokenPatch",
        ):
            await client.async_set_config(BrokenPatch())


async def test_set_config_rejects_patch_model_without_api_name_metadata() -> None:
    """Patch model fields without API metadata should fail with a clear error."""

    @dataclass(frozen=True, slots=True)
    class BrokenPatch(PatchConfigModel):
        mode: PatchConfigValue | None = field(default=None)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with pytest.raises(
            ValueError,
            match=re.escape("Patch model field BrokenPatch.mode must declare api_name metadata"),
        ):
            await client.async_set_config(BrokenPatch(mode=PatchConfigValue(value=2)))


async def test_set_config_invalid_response_raises_duco_error() -> None:
    """Malformed config PATCH responses should raise DucoError."""
    mock_response = _response(json_payload={"General": {"Lan": {"Mode": {"Val": False}}}})

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match=re.escape("Unsupported config value type bool for General.Lan.Mode"),
            ),
        ):
            await client.async_set_config({"General": {"Lan": {"Mode": PatchConfigValue(value=2)}}})


async def test_set_config_api_error_raises_duco_error() -> None:
    """HTTP errors from the generic config PATCH endpoint should surface as DucoError."""
    mock_response = _response(status=400, text_payload="unsupported patch")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match="Unexpected response 400 for /config: unsupported patch",
            ),
        ):
            await client.async_set_config({"General": {"Lan": {"Mode": PatchConfigValue(value=2)}}})


async def test_set_config_connection_error_raises_duco_connection_error() -> None:
    """Transport failures from generic config PATCH should surface as connection errors."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(
                session,
                "request",
                MagicMock(side_effect=aiohttp.ClientError("boom")),
            ),
            pytest.raises(DucoConnectionError, match="Could not reach Duco device"),
        ):
            await client.async_set_config({"General": {"Lan": {"Mode": PatchConfigValue(value=2)}}})


async def test_set_config_write_limit_raises_duco_write_limit_error() -> None:
    """HTTP 429 from generic config PATCH should surface as DucoWriteLimitError."""
    mock_response = _response(status=429)
    request_context = _request_context(mock_response)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", MagicMock(return_value=request_context)),
            pytest.raises(DucoWriteLimitError, match="Duco write capacity exhausted"),
        ):
            await client.async_set_config({"General": {"Lan": {"Mode": PatchConfigValue(value=2)}}})

    request_context.__aexit__.assert_awaited_once()


async def test_get_node_configs_returns_typed_payload(
    node_configs_data: dict[str, object],
) -> None:
    """The node config reader should expose the API-shaped overview payload."""
    mock_response = _response(json_payload=node_configs_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            payload = await client.async_get_node_configs()

    assert isinstance(payload, ConfigNodeOverview)
    assert "params" not in request_mock.call_args.kwargs
    assert payload.nodes == [
        ConfigNode(node_id=1, name=ConfigValueString(value="DucoBox")),
        ConfigNode(node_id=7, name=ConfigValueString(value="Kitchen valve")),
        ConfigNode(node_id=113, name=None),
    ]
    assert payload.raw_payload is node_configs_data
    assert payload.nodes[0].raw_payload is node_configs_data["Nodes"][0]


async def test_get_node_configs_allows_empty_payload() -> None:
    """An empty node config overview should remain a valid typed response."""
    mock_response = _response(json_payload={"Nodes": []})

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            payload = await client.async_get_node_configs()

    assert payload == ConfigNodeOverview(nodes=[])


async def test_get_node_configs_raw_allows_non_name_parameter(
    node_configs_flow_target_data: dict[str, object],
) -> None:
    """The broader raw node config reader should allow non-Name parameters."""
    mock_response = _response(json_payload=node_configs_flow_target_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            payload = await client.async_get_node_configs_raw(parameter="FlowLvlTgt")

    assert payload == node_configs_flow_target_data
    assert request_mock.call_args.kwargs["params"] == {"parameter": "FlowLvlTgt"}


async def test_get_node_configs_forwards_parameter_query(
    node_configs_data: dict[str, object],
) -> None:
    """The optional parameter query should be forwarded unchanged."""
    mock_response = _response(json_payload=node_configs_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            payload = await client.async_get_node_configs(parameter="Name")

    assert isinstance(payload, ConfigNodeOverview)
    assert request_mock.call_args.kwargs["params"] == {"parameter": "Name"}


async def test_get_node_configs_rejects_unsupported_parameter() -> None:
    """Only node fields represented by the typed models should be accepted."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(_response(json_payload={"Nodes": []}))
        with (
            patch.object(session, "request", request_mock),
            pytest.raises(
                ValueError,
                match="async_get_node_configs only supports parameter='Name'",
            ),
        ):
            await client.async_get_node_configs(parameter=cast(Any, "FlowLvlTgt"))

    request_mock.assert_not_called()


@pytest.mark.parametrize(
    ("payload", "message"),
    NODE_CONFIG_MALFORMED_PAYLOADS,
)
async def test_get_node_configs_rejects_malformed_payloads(
    payload: object,
    message: str,
) -> None:
    """Malformed node config payloads should raise DucoError."""
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoError, match=message),
        ):
            await client.async_get_node_configs()


async def test_get_node_configs_api_error_raises_duco_error() -> None:
    """HTTP errors from the node config reader should surface as DucoError."""
    mock_response = _response(status=400, text_payload="unsupported parameter")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match="Unexpected response 400 for /config/nodes: unsupported parameter",
            ),
        ):
            await client.async_get_node_configs(parameter="Name")


async def test_get_node_configs_connection_error_raises_duco_connection_error() -> None:
    """Transport failures from the node config reader should surface as connection errors."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(
                session,
                "request",
                MagicMock(side_effect=aiohttp.ClientError("boom")),
            ),
            pytest.raises(DucoConnectionError, match="Could not reach Duco device"),
        ):
            await client.async_get_node_configs(parameter="Name")


async def test_get_node_config_returns_typed_payload(
    node_config_data: dict[str, object],
) -> None:
    """The single-node config reader should expose the API-shaped payload."""
    mock_response = _response(json_payload=node_config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            payload = await client.async_get_node_config(7)

    assert payload == ConfigNode(
        node_id=7,
        name=ConfigValueString(value="Kitchen valve"),
    )
    assert request_mock.call_args.args[:2] == (
        "GET",
        "http://192.0.2.94/config/nodes/7",
    )
    assert "params" not in request_mock.call_args.kwargs
    assert payload.raw_payload is node_config_data
    assert payload.name is not None
    assert payload.name.raw_payload is node_config_data["Name"]


async def test_get_node_config_forwards_parameter_query(
    node_config_data: dict[str, object],
) -> None:
    """The single-node config reader should forward the optional parameter query."""
    mock_response = _response(json_payload=node_config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            payload = await client.async_get_node_config(7, parameter="Name")

    assert payload == ConfigNode(
        node_id=7,
        name=ConfigValueString(value="Kitchen valve"),
    )
    assert request_mock.call_args.kwargs["params"] == {"parameter": "Name"}


async def test_get_node_config_raw_allows_non_name_parameter(
    node_config_flow_target_data: dict[str, object],
) -> None:
    """The broader raw single-node reader should allow non-Name parameters."""
    mock_response = _response(json_payload=node_config_flow_target_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            payload = await client.async_get_node_config_raw(7, parameter="FlowLvlTgt")

    assert payload == node_config_flow_target_data
    assert request_mock.call_args.kwargs["params"] == {"parameter": "FlowLvlTgt"}


async def test_get_node_config_rejects_unsupported_parameter() -> None:
    """Only single-node config fields represented by the typed models should be accepted."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(_response(json_payload={"Node": 7}))
        with (
            patch.object(session, "request", request_mock),
            pytest.raises(
                ValueError,
                match="async_get_node_config only supports parameter='Name'",
            ),
        ):
            await client.async_get_node_config(7, parameter=cast(Any, "FlowLvlTgt"))

    request_mock.assert_not_called()


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ([], "Expected object payload from /config/nodes/7, got list"),
        ({}, "Expected integer Node in /config/nodes/7 response"),
        (
            {"Node": "7"},
            "Expected integer Node in /config/nodes/7 response, got str",
        ),
        (
            {"Node": 7, "Name": "Kitchen valve"},
            "Expected object for node config value /config/nodes/7.Name, got str",
        ),
        (
            {"Node": 7, "Name": {}},
            "Expected Val in node config value /config/nodes/7.Name",
        ),
        (
            {"Node": 7, "Name": {"Val": 1}},
            "Expected string Val for node config value /config/nodes/7.Name, got int",
        ),
    ],
)
async def test_get_node_config_rejects_malformed_payloads(
    payload: object,
    message: str,
) -> None:
    """Malformed single-node config payloads should raise DucoError."""
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoError, match=message),
        ):
            await client.async_get_node_config(7)


async def test_get_node_config_api_error_raises_duco_error() -> None:
    """HTTP errors from the single-node config reader should surface as DucoError."""
    mock_response = _response(status=404, text_payload="node not found")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match="Unexpected response 404 for /config/nodes/7: node not found",
            ),
        ):
            await client.async_get_node_config(7)


async def test_get_node_config_connection_error_raises_duco_connection_error() -> None:
    """Transport failures from the single-node config reader should surface as connection errors."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(
                session,
                "request",
                MagicMock(side_effect=aiohttp.ClientError("boom")),
            ),
            pytest.raises(DucoConnectionError, match="Could not reach Duco device"),
        ):
            await client.async_get_node_config(7, parameter="Name")


async def test_set_node_config_returns_typed_payload_and_compact_json_body(
    node_config_data: dict[str, object],
) -> None:
    """Node config writes should return a typed payload and compact JSON."""
    mock_response = _response(json_payload=node_config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            payload = await client.async_set_node_config(
                7,
                {"Name": PatchConfigNodeValue(value="Kitchen valve")},
                parameter="Name",
            )

    assert payload == ConfigNode(
        node_id=7,
        name=ConfigValueString(value="Kitchen valve"),
    )
    assert request.call_args.args[:2] == (
        "PATCH",
        "http://192.0.2.94/config/nodes/7",
    )
    _, kwargs = request.call_args
    assert kwargs["params"] == {"parameter": "Name"}
    assert kwargs["data"] == b'{"Name":{"Val":"Kitchen valve"}}'
    assert kwargs["headers"] == {"Content-Type": "application/json"}


async def test_set_node_config_accepts_api_shaped_leaf_payloads(
    node_config_data: dict[str, object],
) -> None:
    """Node config writes should default to `parameter=Name` for typed responses."""
    mock_response = _response(json_payload=node_config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            payload = await client.async_set_node_config(7, {"Name": {"Val": "Kitchen valve"}})

    assert payload == ConfigNode(
        node_id=7,
        name=ConfigValueString(value="Kitchen valve"),
    )
    assert request.call_args.args[:2] == (
        "PATCH",
        "http://192.0.2.94/config/nodes/7",
    )
    _, kwargs = request.call_args
    assert kwargs["params"] == {"parameter": "Name"}
    assert kwargs["data"] == b'{"Name":{"Val":"Kitchen valve"}}'


async def test_set_node_config_accepts_typed_patch_node_struct(
    node_config_data: dict[str, object],
) -> None:
    """Typed node patch models should serialize to the stable Name payload shape."""
    mock_response = _response(json_payload=node_config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            payload = await client.async_set_node_config(
                7,
                PatchConfigNodeStruct(name=PatchConfigNodeValue(value="Kitchen valve")),
            )

    assert payload == ConfigNode(
        node_id=7,
        name=ConfigValueString(value="Kitchen valve"),
    )
    _, kwargs = request.call_args
    assert kwargs["params"] == {"parameter": "Name"}
    assert kwargs["data"] == b'{"Name":{"Val":"Kitchen valve"}}'


async def test_set_node_config_raw_allows_non_name_parameter(
    node_config_flow_target_data: dict[str, object],
) -> None:
    """The broader raw node config writer should allow non-Name parameters."""
    mock_response = _response(json_payload=node_config_flow_target_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            payload = await client.async_set_node_config_raw(
                7,
                {"FlowLvlTgt": PatchConfigNodeValue(value=125)},
                parameter="FlowLvlTgt",
            )

    assert payload == node_config_flow_target_data
    assert request.call_args.args[:2] == (
        "PATCH",
        "http://192.0.2.94/config/nodes/7",
    )
    _, kwargs = request.call_args
    assert kwargs["params"] == {"parameter": "FlowLvlTgt"}
    assert kwargs["data"] == b'{"FlowLvlTgt":{"Val":125}}'
    assert kwargs["headers"] == {"Content-Type": "application/json"}


async def test_set_node_config_raw_returns_none_for_empty_success_response() -> None:
    """The raw node config writer should tolerate empty success responses."""
    mock_response = _response(
        json_side_effect=ValueError("Expecting value: line 1 column 1 (char 0)"),
        text_payload="",
    )

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            payload = await client.async_set_node_config_raw(
                7,
                {"FlowLvlTgt": PatchConfigNodeValue(value=125)},
            )

    assert payload is None
    _, kwargs = request.call_args
    assert "params" not in kwargs
    assert kwargs["data"] == b'{"FlowLvlTgt":{"Val":125}}'


@pytest.mark.parametrize("parameter", [None, "FlowLvlTgt"])
async def test_set_node_config_rejects_unsupported_parameter(
    parameter: object,
) -> None:
    """Only the typed Name field should be accepted for node config PATCH."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(_response(json_payload={"Node": 7}))
        with (
            patch.object(session, "request", request_mock),
            pytest.raises(
                ValueError,
                match="async_set_node_config only supports parameter='Name'",
            ),
        ):
            await client.async_set_node_config(
                7,
                {"Name": {"Val": "Kitchen valve"}},
                parameter=cast(Any, parameter),
            )

    request_mock.assert_not_called()


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {"Name": "Kitchen valve"},
            "Unsupported patch config payload type str for config.nodes.7.Name",
        ),
        (
            {"Name": {"Val": False}},
            "Unsupported patch config value type bool for config.nodes.7.Name",
        ),
        (
            {1: {"Val": "Kitchen valve"}},
            "Expected string key for config.nodes.7, got int",
        ),
        (
            {"Name": {"Val": "Kitchen valve", "Min": 0}},
            "Patch config leaf config.nodes.7.Name may only contain Val",
        ),
    ],
)
async def test_set_node_config_rejects_invalid_patch_payloads(
    payload: object,
    message: str,
) -> None:
    """Invalid node config patch payloads should fail before the request is sent."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with pytest.raises(ValueError, match=message):
            await client.async_set_node_config(7, cast(Any, payload))


async def test_set_node_config_invalid_response_raises_duco_error() -> None:
    """Malformed node config PATCH responses should raise DucoError."""
    mock_response = _response(json_payload={"Node": 7, "Name": {"Val": 1}})

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match=re.escape(
                    "Expected string Val for node config value /config/nodes/7.Name, got int"
                ),
            ),
        ):
            await client.async_set_node_config(
                7,
                {"Name": PatchConfigNodeValue(value="Kitchen valve")},
            )


async def test_set_node_config_api_error_raises_duco_error() -> None:
    """HTTP errors from the node config PATCH endpoint should surface as DucoError."""
    mock_response = _response(status=400, text_payload="unsupported patch")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match="Unexpected response 400 for /config/nodes/7: unsupported patch",
            ),
        ):
            await client.async_set_node_config(
                7,
                {"Name": PatchConfigNodeValue(value="Kitchen valve")},
            )


async def test_set_node_config_connection_error_raises_duco_connection_error() -> None:
    """Transport failures from node config PATCH should surface as connection errors."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(
                session,
                "request",
                MagicMock(side_effect=aiohttp.ClientError("boom")),
            ),
            pytest.raises(DucoConnectionError, match="Could not reach Duco device"),
        ):
            await client.async_set_node_config(
                7,
                {"Name": PatchConfigNodeValue(value="Kitchen valve")},
            )


async def test_set_node_config_write_limit_raises_duco_write_limit_error() -> None:
    """HTTP 429 from node config PATCH should surface as DucoWriteLimitError."""
    mock_response = _response(status=429)
    request_context = _request_context(mock_response)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", MagicMock(return_value=request_context)),
            pytest.raises(DucoWriteLimitError, match="Duco write capacity exhausted"),
        ):
            await client.async_set_node_config(
                7,
                {"Name": PatchConfigNodeValue(value="Kitchen valve")},
            )

    request_context.__aexit__.assert_awaited_once()


async def test_board_info_is_parsed(board_info_data: dict[str, object]) -> None:
    """Test board info parsing."""
    mock_response = _response(json_payload=board_info_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            board = await client.async_get_board_info()

    assert isinstance(board.box_name, BoardName)
    assert board.box_name == "SILENT_CONNECT"
    assert board.box_name.known_value is KnownBoardName.SILENT_CONNECT
    assert board.box_sub_type_name == "Eu"
    assert isinstance(board.serial_board_box, DucoSerialNumber)
    assert board.serial_board_box == "RS0000000001"
    assert isinstance(board.serial_board_comm, DucoSerialNumber)
    assert isinstance(board.serial_duco_box, DucoSerialNumber)
    assert isinstance(board.serial_duco_comm, DucoSerialNumber)
    assert board.time == 1775082497
    assert isinstance(board.public_api_version, DucoVersion)
    assert board.public_api_version == "2.5"
    assert board.public_api_version.components == (2, 5)
    assert board.software_version is None
    assert board.raw_payload is board_info_data["General"]["Board"]


async def test_board_info_with_optional_versions(
    board_info_with_optional_versions_data: dict[str, object],
) -> None:
    """Test board info parsing with SwVersion."""
    mock_response = _response(json_payload=board_info_with_optional_versions_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            board = await client.async_get_board_info()

    assert isinstance(board.public_api_version, DucoVersion)
    assert board.public_api_version == "2.6"
    assert isinstance(board.software_version, DucoVersion)
    assert board.software_version == "2.0.6.0"
    assert board.software_version.components == (2, 0, 6, 0)


async def test_board_info_preserves_unknown_board_and_malformed_versions() -> None:
    """Board parsing should stay forward-tolerant for unknown identities and versions."""
    mock_response = _response(
        json_payload={
            "General": {
                "Board": {
                    "PublicApiVersion": {"Val": "2.beta"},
                    "BoxName": {"Val": "FUTURE_BOX"},
                    "BoxSubTypeName": {"Val": "Prototype"},
                    "SerialBoardBox": {"Val": "RS0000000999"},
                    "SerialBoardComm": {"Val": "PS0000000999"},
                    "SerialDucoBox": {"Val": "P000000-000000-999"},
                    "SerialDucoComm": {"Val": "P000000-000000-998"},
                    "Time": {"Val": 1778600999},
                    "SwVersion": {"Val": "mainline"},
                }
            }
        }
    )

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            board = await client.async_get_board_info()

    assert isinstance(board.box_name, BoardName)
    assert board.box_name == "FUTURE_BOX"
    assert board.box_name.known_value is None
    assert isinstance(board.public_api_version, DucoVersion)
    assert board.public_api_version == "2.beta"
    assert board.public_api_version.components is None
    assert isinstance(board.software_version, DucoVersion)
    assert board.software_version == "mainline"
    assert board.software_version.components is None


async def test_lan_info_wifi_is_parsed(lan_info_data: dict[str, object]) -> None:
    """Test LAN parsing for Wi-Fi connected boxes."""
    mock_response = _response(json_payload=lan_info_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            lan = await client.async_get_lan_info()

    assert isinstance(lan.mode, LanMode)
    assert lan.mode == "WIFI_CLIENT"
    assert lan.mode.known_value is KnownLanMode.WIFI_CLIENT
    assert isinstance(lan.ip, IpAddress)
    assert lan.ip == "192.0.2.94"
    assert isinstance(lan.net_mask, IpAddress)
    assert isinstance(lan.default_gateway, IpAddress)
    assert isinstance(lan.dns, IpAddress)
    assert isinstance(lan.mac, MacAddress)
    assert isinstance(lan.host_name, HostName)
    assert lan.rssi_wifi == -44
    assert lan.raw_payload is lan_info_data["General"]["Lan"]


async def test_lan_info_ethernet_is_parsed(
    lan_info_ethernet_data: dict[str, object],
) -> None:
    """Test LAN parsing for ethernet connected boxes."""
    mock_response = _response(json_payload=lan_info_ethernet_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            lan = await client.async_get_lan_info()

    assert isinstance(lan.mode, LanMode)
    assert lan.mode == "ETHERNET"
    assert lan.mode.known_value is KnownLanMode.ETHERNET
    assert lan.ip == "198.51.100.97"
    assert lan.rssi_wifi is None


async def test_lan_info_preserves_unknown_mode_and_unusual_strings() -> None:
    """LAN parsing should keep forward-looking metadata strings accessible."""
    mock_response = _response(
        json_payload={
            "General": {
                "Lan": {
                    "Mode": {"Val": "FUTURE_WIFI"},
                    "Ip": {"Val": "not-an-ip"},
                    "NetMask": {"Val": "maskish"},
                    "DefaultGateway": {"Val": "gatewayish"},
                    "Dns": {"Val": "dnsish"},
                    "Mac": {"Val": "macish"},
                    "HostName": {"Val": "future host"},
                }
            }
        }
    )

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            lan = await client.async_get_lan_info()

    assert isinstance(lan.mode, LanMode)
    assert lan.mode == "FUTURE_WIFI"
    assert lan.mode.known_value is None
    assert isinstance(lan.ip, IpAddress)
    assert lan.ip == "not-an-ip"
    assert isinstance(lan.mac, MacAddress)
    assert lan.mac == "macish"
    assert isinstance(lan.host_name, HostName)
    assert lan.host_name == "future host"


async def test_get_diagnostics(diag_data: dict[str, object]) -> None:
    """Test diagnostics parsing."""
    mock_response = _response(json_payload=diag_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            diags = await client.async_get_diagnostics()

    assert len(diags) == 3
    assert diags[0].component == "Ventilation"
    assert diags[0].status == "Ok"
    assert diags[0].raw_payload is diag_data["Diag"]["SubSystems"][0]


async def test_get_diagnostics_info_exposes_typed_subsystems(
    diag_data: dict[str, object],
) -> None:
    """Typed diagnostics info should expose an immutable subsystem collection."""
    mock_response = _response(json_payload=diag_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            diag_info = await client.async_get_diagnostics_info()

    assert isinstance(diag_info, DiagInfo)
    assert_type(diag_info, DiagInfo)
    assert_type(diag_info.diagnostic_subsystems, tuple[DiagComponent, ...])
    assert_type(diag_info.diagnostic_subsystems[0].component, str)
    assert_type(diag_info.diagnostic_subsystems[0].status, str)
    assert tuple(item.component for item in diag_info.diagnostic_subsystems) == (
        "Ventilation",
        "VentCool",
        "SunCtrl",
    )
    assert tuple(item.status for item in diag_info.diagnostic_subsystems) == (
        "Ok",
        "Ok",
        "Ok",
    )


async def test_get_diagnostics_preserves_unknown_status() -> None:
    """Unknown diagnostic statuses should be preserved as raw strings."""
    payload: dict[str, object] = {
        "Diag": {
            "SubSystems": [
                {"Component": "Ventilation", "Status": "FutureState"},
            ]
        }
    }
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            diags = await client.async_get_diagnostics()

    assert len(diags) == 1
    assert diags[0].status == "FutureState"


async def test_get_diagnostics_preserves_unknown_component_name() -> None:
    """Unknown diagnostic subsystem names should remain available to consumers."""
    payload: dict[str, object] = {
        "Diag": {
            "SubSystems": [
                {"Component": "FutureSubsystem", "Status": "Ok"},
            ]
        }
    }
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            diag_info = await client.async_get_diagnostics_info()

    assert tuple(item.component for item in diag_info.diagnostic_subsystems) == ("FutureSubsystem",)


@pytest.mark.parametrize(
    ("payload", "expected_raw_payload"),
    [
        pytest.param({}, {}, id="diag-missing"),
        pytest.param({"Diag": {}}, {}, id="subsystems-missing"),
        pytest.param({"Diag": {"SubSystems": []}}, {"SubSystems": []}, id="subsystems-empty"),
    ],
)
async def test_get_diagnostics_info_missing_data_returns_empty_collection(
    payload: dict[str, object],
    expected_raw_payload: dict[str, object],
) -> None:
    """Missing diagnostic data should produce an empty typed subsystem collection."""
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            diag_info = await client.async_get_diagnostics_info()

    assert diag_info.diagnostic_subsystems == ()
    assert diag_info.raw_payload == expected_raw_payload


async def test_get_diagnostics_info_skips_partial_entries() -> None:
    """Incomplete diagnostic entries should be ignored instead of failing parsing."""
    payload: dict[str, object] = {
        "Diag": {
            "SubSystems": [
                {"Component": "Ventilation", "Status": "Ok"},
                {"Component": "VentCool"},
                {"Status": "Error"},
                {},
                "not-a-dict",
                {"Component": "SunCtrl", "Status": "FutureState"},
            ]
        }
    }
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            diag_info = await client.async_get_diagnostics_info()

    assert tuple((item.component, item.status) for item in diag_info.diagnostic_subsystems) == (
        ("Ventilation", "Ok"),
        ("SunCtrl", "FutureState"),
    )


async def test_get_diagnostics_info_does_not_filter_product_specific_subsystems() -> None:
    """Subsystems should be passed through without product-specific filtering."""
    payload: dict[str, object] = {
        "Diag": {
            "SubSystems": [
                {"Component": "Ventilation", "Status": "Error"},
                {"Component": "VentCool", "Status": "Ok"},
                {"Component": "SunCtrl", "Status": "Ok"},
                {"Component": "FutureSubsystem", "Status": "Disable"},
            ]
        }
    }
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            diag_info = await client.async_get_diagnostics_info()

    assert tuple(item.component for item in diag_info.diagnostic_subsystems) == (
        "Ventilation",
        "VentCool",
        "SunCtrl",
        "FutureSubsystem",
    )


async def test_get_nodes_parses_full_payload(nodes_data: dict[str, object]) -> None:
    """Test node parsing across box and sensor nodes."""
    mock_response = _response(json_payload=nodes_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            nodes = await client.async_get_nodes()

    assert len(nodes) == 3

    box = nodes[0]
    assert box.node_id == 1
    assert box.general.node_type == NodeType.BOX
    assert isinstance(box.general.sub_type, NodeSubtype)
    assert box.general.network_type == NetworkType.VIRT
    assert isinstance(box.general.parent, NodeParentId)
    assert isinstance(box.general.asso, NodeAssociationId)
    assert isinstance(box.general.name, NodeName)
    assert isinstance(box.general.identify, NodeIdentify)
    assert box.ventilation is not None
    assert box.ventilation.state == VentilationState.CNT1
    assert isinstance(box.ventilation.time_state_remain, VentilationTimeRemaining)
    assert isinstance(box.ventilation.time_state_end, VentilationTimeEnd)
    assert box.ventilation.flow_lvl_tgt == 15
    assert isinstance(box.ventilation.flow_lvl_tgt, VentilationFlowLevelTarget)
    assert box.sensor is not None
    assert box.sensor.rh == 35.5
    assert isinstance(box.sensor.rh, NodeRelativeHumidity)
    assert box.sensor.iaq_rh == 83
    assert isinstance(box.sensor.iaq_rh, NodeAirQualityIndex)
    assert box.sensor.co2 is None
    assert box.sensor.temp == 27.9
    assert isinstance(box.sensor.temp, NodeTemperature)
    assert box.motor_state is not None
    assert box.motor_state.device_type == 2
    assert isinstance(box.motor_state.device_type, NodeMotorDeviceType)
    assert box.motor_state.req == 1
    assert isinstance(box.motor_state.req, NodeMotorRequest)
    assert box.motor_state.pos_req == 150
    assert isinstance(box.motor_state.pos_req, NodeMotorPosition)
    assert box.motor_state.pos == 143
    assert isinstance(box.motor_state.pos, NodeMotorPosition)
    assert box.raw_payload is nodes_data["Nodes"][0]
    assert box.general.raw_payload is nodes_data["Nodes"][0]["General"]
    assert box.ventilation.raw_payload is nodes_data["Nodes"][0]["Ventilation"]
    assert box.sensor.raw_payload is nodes_data["Nodes"][0]["Sensor"]
    assert box.motor_state.raw_payload is nodes_data["Nodes"][0]["MotorStateCtrl"]

    ucco2 = nodes[1]
    assert ucco2.general.node_type == NodeType.UCCO2
    assert ucco2.general.network_type == NetworkType.RF
    assert ucco2.sensor is not None
    assert ucco2.sensor.co2 == 536
    assert isinstance(ucco2.sensor.co2, NodeCo2Ppm)
    assert ucco2.sensor.iaq_co2 == 100
    assert isinstance(ucco2.sensor.iaq_co2, NodeAirQualityIndex)
    assert ucco2.motor_state is None


async def test_get_nodes_preserves_unknown_sections_in_raw_payload() -> None:
    """Node models should keep unmapped API sections available via raw_payload."""
    payload: dict[str, object] = {
        "Nodes": [
            {
                "Node": 1,
                "General": {
                    "Type": {"Val": "BOX"},
                    "SubType": {"Val": 1},
                    "NetworkType": {"Val": "VIRT"},
                    "Parent": {"Val": 0},
                    "Asso": {"Val": 0},
                    "Name": {"Val": "Kitchen"},
                    "Identify": {"Val": 0},
                    "FirmwareFamily": {"Val": "future"},
                },
                "Sensor": {
                    "Temp": {"Val": 20.1},
                    "Voc": {"Val": 321},
                },
                "CustomSection": {
                    "FutureFlag": {"Val": True},
                },
            }
        ]
    }
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            nodes = await client.async_get_nodes()

    node = nodes[0]
    assert node.general.name == "Kitchen"
    assert isinstance(node.general.name, NodeName)
    assert node.general.raw_payload["FirmwareFamily"] == {"Val": "future"}
    assert node.sensor is not None
    assert node.sensor.temp == 20.1
    assert isinstance(node.sensor.temp, NodeTemperature)
    assert node.sensor.raw_payload["Voc"] == {"Val": 321}
    assert node.raw_payload["CustomSection"] == {"FutureFlag": {"Val": True}}


async def test_get_zones_info_parses_payload(zones_info_data: dict[str, object]) -> None:
    """Zone overview parsing should stay close to the published API shape."""
    mock_response = _response(json_payload=zones_info_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            zones = await client.async_get_zones_info()

    assert zones == InfoZonesOverview(
        zones=[
            InfoZone(
                zone_id=1,
                name="Ground floor",
                groups=[
                    InfoGroup(group_id=1, nodes=[7, 8]),
                    InfoGroup(group_id=2, nodes=[]),
                ],
            ),
            InfoZone(zone_id=2),
        ]
    )
    assert zones.raw_payload is zones_info_data
    assert zones.zones[0].raw_payload is zones_info_data["Zones"][0]
    assert zones.zones[0].groups[0].raw_payload is zones_info_data["Zones"][0]["Groups"][0]
    assert zones.zones[0].raw_payload["FutureZoneField"] == {"Val": "kept"}
    assert zones.zones[0].groups[0].raw_payload["FutureGroupField"] == {"Val": True}


async def test_get_zones_info_uses_zone_path(zones_info_data: dict[str, object]) -> None:
    """The zone overview reader should request the published zone info endpoint."""
    mock_response = _response(json_payload=zones_info_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            await client.async_get_zones_info()

    assert request_mock.call_args.args[:2] == (
        "GET",
        "http://192.0.2.94/info/zones",
    )
    assert "params" not in request_mock.call_args.kwargs


@pytest.mark.parametrize(("payload", "message"), ZONES_INFO_MALFORMED_PAYLOADS)
async def test_get_zones_info_malformed_payload_raises_duco_error(
    payload: object,
    message: str,
) -> None:
    """Malformed zone overview payloads should raise DucoError."""
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoError, match=message),
        ):
            await client.async_get_zones_info()


async def test_get_zones_info_api_error_raises_duco_error() -> None:
    """HTTP errors from the zone overview should surface as DucoError."""
    mock_response = _response(status=503, text_payload="service unavailable")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match="Unexpected response 503 for /info/zones: service unavailable",
            ),
        ):
            await client.async_get_zones_info()


async def test_get_zones_info_connection_error_raises_duco_connection_error() -> None:
    """Transport failures from the zone overview should surface as connection errors."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(
                session,
                "request",
                MagicMock(side_effect=aiohttp.ClientError("boom")),
            ),
            pytest.raises(DucoConnectionError, match="Could not reach Duco device"),
        ):
            await client.async_get_zones_info()


async def test_get_zone_info_parses_payload(zone_info_data: dict[str, object]) -> None:
    """Single-zone parsing should stay close to the published API shape."""
    mock_response = _response(json_payload=zone_info_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            zone = await client.async_get_zone_info(1)

    assert zone == InfoZone(
        zone_id=1,
        name="Ground floor",
        groups=[
            InfoGroup(group_id=1, nodes=[7, 8]),
            InfoGroup(group_id=2, nodes=[]),
        ],
    )
    assert zone.raw_payload is zone_info_data
    assert zone.groups[0].raw_payload is zone_info_data["Groups"][0]
    assert zone.raw_payload["FutureZoneField"] == {"Val": "kept"}
    assert zone.groups[0].raw_payload["FutureGroupField"] == {"Val": True}


async def test_get_zone_info_uses_zone_path(zone_info_data: dict[str, object]) -> None:
    """The single-zone reader should request the zone-specific endpoint."""
    mock_response = _response(json_payload=zone_info_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            await client.async_get_zone_info(1)

    assert request_mock.call_args.args[:2] == (
        "GET",
        "http://192.0.2.94/info/zones/1",
    )
    assert "params" not in request_mock.call_args.kwargs


async def test_get_zone_info_forwards_query_params(
    zone_info_data: dict[str, object],
) -> None:
    """The single-zone reader should forward optional query parameters."""
    mock_response = _response(json_payload=zone_info_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            await client.async_get_zone_info(
                1,
                group=2,
                module="Groups",
                submodule="General",
                parameter="Nodes",
            )

    assert request_mock.call_args.args[:2] == (
        "GET",
        "http://192.0.2.94/info/zones/1",
    )
    assert request_mock.call_args.kwargs["params"] == {
        "group": "2",
        "module": "Groups",
        "submodule": "General",
        "parameter": "Nodes",
    }


async def test_get_zone_info_accepts_selector_enums(
    zone_info_data: dict[str, object],
) -> None:
    """Known zone selector enums should serialize to the documented raw query values."""
    mock_response = _response(json_payload=zone_info_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            await client.async_get_zone_info(
                1,
                group=2,
                module=ZoneModuleSelector.DEVICE_GROUP_CONFIG,
                submodule=DeviceGroupConfigSubmoduleSelector.GENERAL,
                parameter="Name",
            )

    assert request_mock.call_args.kwargs["params"] == {
        "group": "2",
        "module": "DeviceGroupConfig",
        "submodule": "General",
        "parameter": "Name",
    }


@pytest.mark.parametrize(("payload", "message"), ZONE_INFO_MALFORMED_PAYLOADS)
async def test_get_zone_info_malformed_payload_raises_duco_error(
    payload: object,
    message: str,
) -> None:
    """Malformed single-zone payloads should raise DucoError."""
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoError, match=message),
        ):
            await client.async_get_zone_info(1)


async def test_get_zone_info_api_error_raises_duco_error() -> None:
    """HTTP errors from the single-zone endpoint should surface as DucoError."""
    mock_response = _response(status=404, text_payload="zone not found")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match="Unexpected response 404 for /info/zones/1: zone not found",
            ),
        ):
            await client.async_get_zone_info(1)


async def test_get_zone_info_connection_error_raises_duco_connection_error() -> None:
    """Transport failures from the single-zone endpoint should surface as connection errors."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(
                session,
                "request",
                MagicMock(side_effect=aiohttp.ClientError("boom")),
            ),
            pytest.raises(DucoConnectionError, match="Could not reach Duco device"),
        ):
            await client.async_get_zone_info(1)


async def test_get_zones_config_parses_payload(
    zones_config_data: dict[str, object],
) -> None:
    """Zone config parsing should keep typed names and group identifiers."""
    mock_response = _response(json_payload=zones_config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            zones = await client.async_get_zones_config()

    assert zones == ConfigZonesOverview(
        zones=[
            ConfigZone(
                zone_id=1,
                name=ConfigValueString(value="Ground floor"),
                groups=[
                    ConfigGroup(group_id=1),
                    ConfigGroup(group_id=2),
                ],
            ),
            ConfigZone(zone_id=2),
        ]
    )
    assert zones.raw_payload is zones_config_data
    assert zones.zones[0].raw_payload is zones_config_data["Zones"][0]
    assert zones.zones[0].name is not None
    assert (
        zones.zones[0].name.raw_payload
        is zones_config_data["Zones"][0]["DeviceGroupConfig"]["General"]["Name"]
    )
    assert zones.zones[0].groups[0].raw_payload is zones_config_data["Zones"][0]["Groups"][0]
    assert zones.zones[0].raw_payload["FutureZoneField"] == {"Val": "kept"}
    assert zones.zones[0].groups[0].raw_payload["FutureGroupField"] == {"Val": True}


async def test_get_zones_config_allows_empty_payload() -> None:
    """An empty zone config overview should remain a valid typed response."""
    mock_response = _response(json_payload={"Zones": []})

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            payload = await client.async_get_zones_config()

    assert payload == ConfigZonesOverview(zones=[])


async def test_get_zones_config_uses_zone_path(
    zones_config_data: dict[str, object],
) -> None:
    """The zone config reader should request the published overview endpoint."""
    mock_response = _response(json_payload=zones_config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            await client.async_get_zones_config()

    assert request_mock.call_args.args[:2] == (
        "GET",
        "http://192.0.2.94/config/zones",
    )
    assert "params" not in request_mock.call_args.kwargs


async def test_get_zones_config_forwards_query_params(
    zones_config_data: dict[str, object],
) -> None:
    """The zone config reader should forward documented optional query parameters."""
    mock_response = _response(json_payload=zones_config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            await client.async_get_zones_config(
                zone=1,
                group=2,
                module="Groups",
                submodule="General",
                parameter="Name",
            )

    assert request_mock.call_args.args[:2] == (
        "GET",
        "http://192.0.2.94/config/zones",
    )
    assert request_mock.call_args.kwargs["params"] == {
        "zone": "1",
        "group": "2",
        "module": "Groups",
        "submodule": "General",
        "parameter": "Name",
    }


@pytest.mark.parametrize(("payload", "message"), ZONES_CONFIG_MALFORMED_PAYLOADS)
async def test_get_zones_config_rejects_malformed_payloads(
    payload: object,
    message: str,
) -> None:
    """Malformed zone config payloads should raise DucoError."""
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoError, match=message),
        ):
            await client.async_get_zones_config()


async def test_get_zones_config_api_error_raises_duco_error() -> None:
    """HTTP errors from the zone config endpoint should surface as DucoError."""
    mock_response = _response(status=400, text_payload="unsupported parameter")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match="Unexpected response 400 for /config/zones: unsupported parameter",
            ),
        ):
            await client.async_get_zones_config(parameter="Name")


async def test_get_zones_config_connection_error_raises_duco_connection_error() -> None:
    """Transport failures from the zone config endpoint should surface as connection errors."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(
                session,
                "request",
                MagicMock(side_effect=aiohttp.ClientError("boom")),
            ),
            pytest.raises(DucoConnectionError, match="Could not reach Duco device"),
        ):
            await client.async_get_zones_config(parameter="Name")


async def test_get_zone_config_parses_payload(
    zone_config_data: dict[str, object],
) -> None:
    """Single-zone config parsing should keep typed names and group identifiers."""
    mock_response = _response(json_payload=zone_config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            zone = await client.async_get_zone_config(1)

    assert zone == ConfigZone(
        zone_id=1,
        name=ConfigValueString(value="Ground floor"),
        groups=[
            ConfigGroup(group_id=1),
            ConfigGroup(group_id=2),
        ],
    )
    assert zone.raw_payload is zone_config_data
    assert zone.name is not None
    assert zone.name.raw_payload is zone_config_data["DeviceGroupConfig"]["General"]["Name"]
    assert zone.groups[0].raw_payload is zone_config_data["Groups"][0]
    assert zone.raw_payload["FutureZoneField"] == {"Val": "kept"}
    assert zone.groups[0].raw_payload["FutureGroupField"] == {"Val": True}


async def test_get_zone_config_uses_zone_path(
    zone_config_data: dict[str, object],
) -> None:
    """The single-zone config reader should request the published zone endpoint."""
    mock_response = _response(json_payload=zone_config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            await client.async_get_zone_config(1)

    assert request_mock.call_args.args[:2] == (
        "GET",
        "http://192.0.2.94/config/zones/1",
    )
    assert "params" not in request_mock.call_args.kwargs


async def test_get_zone_config_forwards_query_params(
    zone_config_data: dict[str, object],
) -> None:
    """The single-zone config reader should forward documented query parameters."""
    mock_response = _response(json_payload=zone_config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            await client.async_get_zone_config(
                1,
                group=2,
                module="Groups",
                submodule="General",
                parameter="Name",
            )

    assert request_mock.call_args.args[:2] == (
        "GET",
        "http://192.0.2.94/config/zones/1",
    )
    assert request_mock.call_args.kwargs["params"] == {
        "group": "2",
        "module": "Groups",
        "submodule": "General",
        "parameter": "Name",
    }


@pytest.mark.parametrize(("payload", "message"), ZONE_CONFIG_MALFORMED_PAYLOADS)
async def test_get_zone_config_rejects_malformed_payloads(
    payload: object,
    message: str,
) -> None:
    """Malformed single-zone config payloads should raise DucoError."""
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoError, match=message),
        ):
            await client.async_get_zone_config(1)


async def test_get_zone_config_api_error_raises_duco_error() -> None:
    """HTTP errors from the single-zone config endpoint should surface as DucoError."""
    mock_response = _response(status=404, text_payload="zone not found")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match="Unexpected response 404 for /config/zones/1: zone not found",
            ),
        ):
            await client.async_get_zone_config(1)


async def test_get_zone_config_connection_error_raises_duco_connection_error() -> None:
    """Transport failures from the single-zone config endpoint should surface
    as connection errors.
    """
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(
                session,
                "request",
                MagicMock(side_effect=aiohttp.ClientError("boom")),
            ),
            pytest.raises(DucoConnectionError, match="Could not reach Duco device"),
        ):
            await client.async_get_zone_config(1)


async def test_set_zone_config_returns_typed_payload_and_compact_json_body(
    zone_config_data: dict[str, object],
) -> None:
    """Zone config writes should return a typed payload and compact JSON."""
    mock_response = _response(json_payload=zone_config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            payload = await client.async_set_zone_config(
                1,
                {
                    "DeviceGroupConfig": {
                        "General": {"Name": PatchConfigValue(value="Ground floor")}
                    }
                },
            )

    assert payload == ConfigZone(
        zone_id=1,
        name=ConfigValueString(value="Ground floor"),
        groups=[
            ConfigGroup(group_id=1),
            ConfigGroup(group_id=2),
        ],
    )
    assert request.call_args.args[:2] == (
        "PATCH",
        "http://192.0.2.94/config/zones/1",
    )
    _, kwargs = request.call_args
    assert "params" not in kwargs
    assert kwargs["data"] == b'{"DeviceGroupConfig":{"General":{"Name":{"Val":"Ground floor"}}}}'
    assert kwargs["headers"] == {"Content-Type": "application/json"}


async def test_set_zone_config_accepts_typed_zone_patch_model(
    zone_config_data: dict[str, object],
) -> None:
    """Zone config writes should accept the typed zone patch model."""
    mock_response = _response(json_payload=zone_config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            payload = await client.async_set_zone_config(
                1,
                PatchConfigZoneStruct(
                    device_group_config=PatchConfigZoneDeviceGroupConfig(
                        general=PatchConfigZoneGeneral(name=PatchConfigValue(value="Ground floor"))
                    )
                ),
                module=ZoneModuleSelector.DEVICE_GROUP_CONFIG,
                submodule=DeviceGroupConfigSubmoduleSelector.GENERAL,
                parameter="Name",
            )

    assert payload == ConfigZone(
        zone_id=1,
        name=ConfigValueString(value="Ground floor"),
        groups=[
            ConfigGroup(group_id=1),
            ConfigGroup(group_id=2),
        ],
    )
    _, kwargs = request.call_args
    assert kwargs["params"] == {
        "module": "DeviceGroupConfig",
        "submodule": "General",
        "parameter": "Name",
    }
    assert kwargs["data"] == b'{"DeviceGroupConfig":{"General":{"Name":{"Val":"Ground floor"}}}}'


async def test_set_zone_config_accepts_api_shaped_leaf_payloads(
    zone_config_data: dict[str, object],
) -> None:
    """Zone config writes should also accept raw API-shaped leaf payloads."""
    mock_response = _response(json_payload=zone_config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            payload = await client.async_set_zone_config(
                1,
                {"DeviceGroupConfig": {"General": {"Name": {"Val": "Ground floor"}}}},
            )

    assert payload == ConfigZone(
        zone_id=1,
        name=ConfigValueString(value="Ground floor"),
        groups=[
            ConfigGroup(group_id=1),
            ConfigGroup(group_id=2),
        ],
    )
    _, kwargs = request.call_args
    assert kwargs["data"] == b'{"DeviceGroupConfig":{"General":{"Name":{"Val":"Ground floor"}}}}'


async def test_set_zone_config_forwards_query_params(
    zone_config_data: dict[str, object],
) -> None:
    """Zone config writes should forward documented query parameters."""
    mock_response = _response(json_payload=zone_config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            await client.async_set_zone_config(
                1,
                {"DeviceGroupConfig": {"General": {"Name": {"Val": "Ground floor"}}}},
                module="DeviceGroupConfig",
                submodule="General",
                parameter="Name",
            )

    assert request_mock.call_args.args[:2] == (
        "PATCH",
        "http://192.0.2.94/config/zones/1",
    )
    assert request_mock.call_args.kwargs["params"] == {
        "module": "DeviceGroupConfig",
        "submodule": "General",
        "parameter": "Name",
    }


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {"DeviceGroupConfig": {"General": {"Name": "Ground floor"}}},
            (
                "Unsupported patch config payload type str for "
                "config.zones.1.DeviceGroupConfig.General.Name"
            ),
        ),
        (
            {"DeviceGroupConfig": {"General": {"Name": {"Val": False}}}},
            (
                "Unsupported patch config value type bool for "
                "config.zones.1.DeviceGroupConfig.General.Name"
            ),
        ),
        (
            {1: {"General": {"Name": {"Val": "Ground floor"}}}},
            "Expected string key for config.zones.1, got int",
        ),
        (
            {"DeviceGroupConfig": {"General": {"Name": {"Val": "Ground floor", "Min": 0}}}},
            "Patch config leaf config.zones.1.DeviceGroupConfig.General.Name may only contain Val",
        ),
    ],
)
async def test_set_zone_config_rejects_invalid_patch_payloads(
    payload: object,
    message: str,
) -> None:
    """Invalid zone config patch payloads should fail before the request is sent."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with pytest.raises(ValueError, match=message):
            await client.async_set_zone_config(1, cast(Any, payload))


async def test_set_zone_config_invalid_response_raises_duco_error() -> None:
    """Malformed zone config PATCH responses should raise DucoError."""
    mock_response = _response(
        json_payload={"Zone": 1, "DeviceGroupConfig": {"General": {"Name": {"Val": 1}}}}
    )

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match=re.escape(
                    "Expected string Val for zone config value "
                    "/config/zones/1.DeviceGroupConfig.General.Name, got int"
                ),
            ),
        ):
            await client.async_set_zone_config(
                1,
                {
                    "DeviceGroupConfig": {
                        "General": {"Name": PatchConfigValue(value="Ground floor")}
                    }
                },
            )


async def test_set_zone_config_api_error_raises_duco_error() -> None:
    """HTTP errors from the zone config PATCH endpoint should surface as DucoError."""
    mock_response = _response(status=400, text_payload="unsupported patch")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match="Unexpected response 400 for /config/zones/1: unsupported patch",
            ),
        ):
            await client.async_set_zone_config(
                1,
                {
                    "DeviceGroupConfig": {
                        "General": {"Name": PatchConfigValue(value="Ground floor")}
                    }
                },
            )


async def test_set_zone_config_connection_error_raises_duco_connection_error() -> None:
    """Transport failures from zone config PATCH should surface as connection errors."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(
                session,
                "request",
                MagicMock(side_effect=aiohttp.ClientError("boom")),
            ),
            pytest.raises(DucoConnectionError, match="Could not reach Duco device"),
        ):
            await client.async_set_zone_config(
                1,
                {
                    "DeviceGroupConfig": {
                        "General": {"Name": PatchConfigValue(value="Ground floor")}
                    }
                },
            )


async def test_set_zone_config_write_limit_raises_duco_write_limit_error() -> None:
    """HTTP 429 from zone config PATCH should surface as DucoWriteLimitError."""
    mock_response = _response(status=429)
    request_context = _request_context(mock_response)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", MagicMock(return_value=request_context)),
            pytest.raises(DucoWriteLimitError, match="Duco write capacity exhausted"),
        ):
            await client.async_set_zone_config(
                1,
                {
                    "DeviceGroupConfig": {
                        "General": {"Name": PatchConfigValue(value="Ground floor")}
                    }
                },
            )

    request_context.__aexit__.assert_awaited_once()


async def test_get_zone_group_info_parses_payload(
    zone_group_info_data: dict[str, object],
) -> None:
    """Zone-group parsing should keep both identifiers and typed nodes."""
    mock_response = _response(json_payload=zone_group_info_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            zone_group = await client.async_get_zone_group_info(1, 2)

    assert zone_group == InfoZoneGroup(zone_id=1, group_id=2, nodes=[11, 12])
    assert zone_group.raw_payload is zone_group_info_data
    assert zone_group.raw_payload["FutureGroupField"] == {"Val": True}


async def test_get_zone_group_info_uses_zone_group_path(
    zone_group_info_data: dict[str, object],
) -> None:
    """The zone-group reader should request the published group endpoint."""
    mock_response = _response(json_payload=zone_group_info_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            await client.async_get_zone_group_info(1, 2)

    assert request_mock.call_args.args[:2] == (
        "GET",
        "http://192.0.2.94/info/zones/1/groups/2",
    )
    assert "params" not in request_mock.call_args.kwargs


async def test_get_zone_group_info_forwards_query_params(
    zone_group_info_data: dict[str, object],
) -> None:
    """The zone-group reader should forward optional query parameters."""
    mock_response = _response(json_payload=zone_group_info_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            await client.async_get_zone_group_info(
                1,
                2,
                module="Groups",
                submodule="General",
                parameter="Nodes",
            )

    assert request_mock.call_args.args[:2] == (
        "GET",
        "http://192.0.2.94/info/zones/1/groups/2",
    )
    assert request_mock.call_args.kwargs["params"] == {
        "module": "Groups",
        "submodule": "General",
        "parameter": "Nodes",
    }


@pytest.mark.parametrize(("payload", "message"), ZONE_GROUP_INFO_MALFORMED_PAYLOADS)
async def test_get_zone_group_info_malformed_payload_raises_duco_error(
    payload: object,
    message: str,
) -> None:
    """Malformed zone-group payloads should raise DucoError."""
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoError, match=message),
        ):
            await client.async_get_zone_group_info(1, 2)


async def test_get_zone_group_info_api_error_raises_duco_error() -> None:
    """HTTP errors from the zone-group endpoint should surface as DucoError."""
    mock_response = _response(status=404, text_payload="group not found")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match=("Unexpected response 404 for /info/zones/1/groups/2: group not found"),
            ),
        ):
            await client.async_get_zone_group_info(1, 2)


async def test_get_zone_group_info_connection_error_raises_duco_connection_error() -> None:
    """Transport failures from the zone-group endpoint should surface as connection errors."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(
                session,
                "request",
                MagicMock(side_effect=aiohttp.ClientError("boom")),
            ),
            pytest.raises(DucoConnectionError, match="Could not reach Duco device"),
        ):
            await client.async_get_zone_group_info(1, 2)


async def test_get_nodes_overview_parses_payload(
    nodes_overview_data: list[dict[str, int]],
) -> None:
    """Test lightweight node overview parsing."""
    mock_response = _response(json_payload=nodes_overview_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            nodes = await client.async_get_nodes_overview()

    assert nodes == [
        NodeOverview(node_id=1),
        NodeOverview(node_id=2),
        NodeOverview(node_id=113),
    ]
    assert nodes[0].raw_payload is nodes_overview_data[0]


async def test_get_nodes_overview_handles_empty_payload() -> None:
    """The lightweight node overview should allow empty responses."""
    mock_response = _response(json_payload=[])

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            nodes = await client.async_get_nodes_overview()

    assert nodes == []


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"Nodes": [{"Node": 1}]}, "Expected list payload from /nodes, got dict"),
        ([{}], "Expected integer Node in /nodes item at index 0"),
        ([{"Node": "1"}], "Expected integer Node in /nodes item at index 0, got str"),
    ],
)
async def test_get_nodes_overview_malformed_payload_raises_duco_error(
    payload: object,
    message: str,
) -> None:
    """Malformed lightweight node overview payloads should raise DucoError."""
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoError, match=message),
        ):
            await client.async_get_nodes_overview()


async def test_get_nodes_overview_api_error_raises_duco_error() -> None:
    """HTTP errors from the lightweight node overview should surface as DucoError."""
    mock_response = _response(status=503, text_payload="service unavailable")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match="Unexpected response 503 for /nodes: service unavailable",
            ),
        ):
            await client.async_get_nodes_overview()


async def test_get_nodes_overview_connection_error_raises_duco_connection_error() -> None:
    """Transport failures from the lightweight node overview should surface as connection errors."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(
                session,
                "request",
                MagicMock(side_effect=aiohttp.ClientError("boom")),
            ),
            pytest.raises(DucoConnectionError, match="Could not reach Duco device"),
        ):
            await client.async_get_nodes_overview()


async def test_get_node_info_parses_payload(node_data: dict[str, object]) -> None:
    """Test single-node detail parsing."""
    mock_response = _response(json_payload=node_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            node = await client.async_get_node_info(2)

    assert node.node_id == 2
    assert node.general.node_type == NodeType.UCCO2
    assert node.general.network_type == NetworkType.RF
    assert isinstance(node.general.name, NodeName)
    assert node.sensor is not None
    assert node.sensor.co2 == 536
    assert isinstance(node.sensor.co2, NodeCo2Ppm)
    assert node.sensor.iaq_co2 == 100
    assert isinstance(node.sensor.iaq_co2, NodeAirQualityIndex)
    assert node.motor_state is None
    assert node.raw_payload is node_data


async def test_get_node_info_uses_node_path(node_data: dict[str, object]) -> None:
    """The single-node reader should request the node-specific endpoint."""
    mock_response = _response(json_payload=node_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            await client.async_get_node_info(2)

    assert request_mock.call_args.args[:2] == (
        "GET",
        "http://192.0.2.94/info/nodes/2",
    )
    assert "params" not in request_mock.call_args.kwargs


async def test_get_node_info_forwards_query_params(node_data: dict[str, object]) -> None:
    """The single-node reader should forward optional query parameters."""
    mock_response = _response(json_payload=node_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            await client.async_get_node_info(2, module="Sensor", parameter="Co2")

    assert request_mock.call_args.args[:2] == (
        "GET",
        "http://192.0.2.94/info/nodes/2",
    )
    assert request_mock.call_args.kwargs["params"] == {
        "module": "Sensor",
        "parameter": "Co2",
    }


async def test_get_node_info_accepts_selector_enums(node_data: dict[str, object]) -> None:
    """Known node selector enums should serialize to the documented raw query values."""
    mock_response = _response(json_payload=node_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            await client.async_get_node_info(
                2,
                module=NodeInfoModuleSelector.SENSOR,
                parameter="Co2",
            )

    assert request_mock.call_args.kwargs["params"] == {
        "module": "Sensor",
        "parameter": "Co2",
    }


async def test_set_config_accepts_selector_enums(
    config_data: dict[str, object],
) -> None:
    """Known config selector enums should also serialize correctly for writes."""
    mock_response = _response(json_payload=config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            await client.async_set_config(
                {"General": {"Lan": {"Mode": PatchConfigValue(value=2)}}},
                module=ConfigModuleSelector.GENERAL,
                submodule=ConfigGeneralSubmoduleSelector.LAN,
                parameter="Mode",
            )

    assert request.call_args.args[:2] == (
        "PATCH",
        "http://192.0.2.94/config",
    )
    assert request.call_args.kwargs["params"] == {
        "module": "General",
        "submodule": "Lan",
        "parameter": "Mode",
    }


async def test_get_node_info_api_error_raises_duco_error() -> None:
    """HTTP errors from the single-node endpoint should surface as DucoError."""
    mock_response = _response(status=404, text_payload="node not found")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match="Unexpected response 404 for /info/nodes/2: node not found",
            ),
        ):
            await client.async_get_node_info(2)


async def test_get_node_info_connection_error_raises_duco_connection_error() -> None:
    """Transport failures from the single-node endpoint should surface as connection errors."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(
                session,
                "request",
                MagicMock(side_effect=aiohttp.ClientError("boom")),
            ),
            pytest.raises(DucoConnectionError, match="Could not reach Duco device"),
        ):
            await client.async_get_node_info(2)


async def test_get_nodes_unknown_network_type_falls_back_to_unknown() -> None:
    """Test that unknown network types do not crash parsing."""
    payload: dict[str, object] = {
        "Nodes": [
            {
                "Node": 4,
                "General": {
                    "Type": {"Val": "UCCO2"},
                    "SubType": {"Val": 0},
                    "NetworkType": {"Val": "FUTURE_TYPE"},
                    "Parent": {"Val": 1},
                    "Asso": {"Val": 1},
                    "Name": {"Val": ""},
                    "Identify": {"Val": 0},
                },
                "Ventilation": {
                    "State": {"Val": "AUTO"},
                    "TimeStateRemain": {"Val": 0},
                    "TimeStateEnd": {"Val": 0},
                    "Mode": {"Val": "-"},
                },
            }
        ]
    }
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            nodes = await client.async_get_nodes()

    assert len(nodes) == 1
    assert nodes[0].general.network_type == NetworkType.UNKNOWN


async def test_get_nodes_unknown_network_type_logs_fallback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unknown enum fallbacks should emit a debug log for troubleshooting."""
    payload: dict[str, object] = {
        "Nodes": [
            {
                "Node": 4,
                "General": {
                    "Type": {"Val": "UCCO2"},
                    "SubType": {"Val": 0},
                    "NetworkType": {"Val": "FUTURE_TYPE"},
                    "Parent": {"Val": 1},
                    "Asso": {"Val": 1},
                    "Name": {"Val": ""},
                    "Identify": {"Val": 0},
                },
                "Ventilation": {
                    "State": {"Val": "AUTO"},
                    "TimeStateRemain": {"Val": 0},
                    "TimeStateEnd": {"Val": 0},
                    "Mode": {"Val": "-"},
                },
            }
        ]
    }
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            caplog.at_level(logging.DEBUG, logger="duco_connectivity.client"),
            patch.object(session, "request", _request(mock_response)),
        ):
            await client.async_get_nodes()

    assert "Unknown network type 'FUTURE_TYPE' received from Duco API" in caplog.text


@pytest.mark.parametrize(
    ("raw_network_type", "expected_network_type"),
    [
        ("-", NetworkType.NONE),
        ("WI", NetworkType.WI),
        ("RF", NetworkType.RF),
        ("VIRT", NetworkType.VIRT),
        ("MB", NetworkType.MB),
    ],
)
async def test_get_nodes_known_network_type_is_parsed(
    raw_network_type: str,
    expected_network_type: NetworkType,
) -> None:
    """Documented network types should parse without fallback."""
    payload: dict[str, object] = {
        "Nodes": [
            {
                "Node": 4,
                "General": {
                    "Type": {"Val": "UCCO2"},
                    "SubType": {"Val": 0},
                    "NetworkType": {"Val": raw_network_type},
                    "Parent": {"Val": 1},
                    "Asso": {"Val": 1},
                    "Name": {"Val": ""},
                    "Identify": {"Val": 0},
                },
                "Ventilation": {
                    "State": {"Val": "AUTO"},
                    "TimeStateRemain": {"Val": 0},
                    "TimeStateEnd": {"Val": 0},
                    "Mode": {"Val": "-"},
                },
            }
        ]
    }
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            nodes = await client.async_get_nodes()

    assert len(nodes) == 1
    assert nodes[0].general.network_type is expected_network_type


async def test_get_nodes_unknown_node_type_falls_back_to_unknown() -> None:
    """Test that unknown node types do not crash parsing."""
    payload: dict[str, object] = {
        "Nodes": [
            {
                "Node": 5,
                "General": {
                    "Type": {"Val": "FUTURE_NODE"},
                    "SubType": {"Val": 0},
                    "NetworkType": {"Val": "RF"},
                    "Parent": {"Val": 1},
                    "Asso": {"Val": 1},
                    "Name": {"Val": ""},
                    "Identify": {"Val": 0},
                },
            }
        ]
    }
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            nodes = await client.async_get_nodes()

    assert len(nodes) == 1
    assert nodes[0].general.node_type == NodeType.UNKNOWN


@pytest.mark.parametrize(
    "node_type",
    [
        "UNKN",
        "IQ",
        "CO2",
        "RH",
        "KLEP",
        "TOP",
        "COMB",
        "CLIMA",
        "UCVOC",
        "UCSUN",
        "UCVENT",
        "VLVRH",
        "VLVVOC",
        "VLVCO2",
        "SWITCH",
        "ACTUAT",
        "UCBATRH",
        "PWMIN",
        "IAV",
        "IAVRH",
        "IAVVOC",
        "IAVCO2",
        "EAV",
        "EAVRH",
        "EAVVOC",
        "EAVCO2",
        "BOIILER",
        "TRONIC",
        "VLVCO2RH",
        "BSCO2",
        "BSVOC",
        "MOTORRLY",
        "MOTORMB",
        "WXSENSOR",
        "DI",
        "DO",
        "COMM",
        "RLYMB",
        "PERILEX",
        "RO",
    ],
)
async def test_get_nodes_known_spec_node_types_are_parsed(node_type: str) -> None:
    """Spec-defined node types should map to concrete enum members."""
    payload: dict[str, object] = {
        "Nodes": [
            {
                "Node": 5,
                "General": {
                    "Type": {"Val": node_type},
                    "SubType": {"Val": 0},
                    "NetworkType": {"Val": "RF"},
                    "Parent": {"Val": 1},
                    "Asso": {"Val": 1},
                    "Name": {"Val": ""},
                    "Identify": {"Val": 0},
                },
            }
        ]
    }
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            nodes = await client.async_get_nodes()

    assert len(nodes) == 1
    assert nodes[0].general.node_type == NodeType(node_type)


async def test_get_ventilation_temperature_info_is_parsed(
    ventilation_info_data: dict[str, object],
) -> None:
    """Ventilation temperatures should be converted from decicelsius to Celsius."""
    mock_response = _response(json_payload=ventilation_info_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            payload = await client.async_get_ventilation_temperature_info()

    assert_type(payload, VentilationTemperatureInfo)
    assert payload == VentilationTemperatureInfo(
        temp_oda=17.5,
        temp_sup=18.0,
        temp_eta=21.5,
        temp_eha=22.5,
    )
    assert payload.raw_payload is ventilation_info_data["Ventilation"]["Sensor"]


async def test_get_ventilation_temperature_info_returns_empty_model_when_sensor_missing() -> None:
    """Missing ventilation sensors should return an empty typed model."""
    mock_response = _response(json_payload={"Ventilation": {}})

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            payload = await client.async_get_ventilation_temperature_info()

    assert payload == VentilationTemperatureInfo()
    assert payload.raw_payload == {}


async def test_get_ventilation_temperature_info_raises_for_unsupported_module() -> None:
    """Unsupported ventilation modules should raise a typed capability error."""
    mock_response = _response(
        status=400,
        text_payload='{"Code":3,"Result":"FAILED"}',
    )

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoUnsupportedCapabilityError) as err_info,
        ):
            await client.async_get_ventilation_temperature_info()

    assert err_info.value.status == 400
    assert err_info.value.path == "/info"


async def test_get_ventilation_temperature_info_reraises_other_client_errors() -> None:
    """Unexpected ventilation endpoint failures should remain visible to callers."""
    mock_response = _response(status=400, text_payload='{"Code":4,"Result":"FAILED"}')

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoResponseError),
        ):
            await client.async_get_ventilation_temperature_info()


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        pytest.param(
            [],
            "Expected object payload from /info?module=Ventilation, got list",
            id="root_not_object",
        ),
        pytest.param(
            {"Ventilation": []},
            "Expected object payload at Ventilation in /info?module=Ventilation response",
            id="ventilation_not_object",
        ),
        pytest.param(
            {"Ventilation": {"Sensor": []}},
            "Expected object payload at Ventilation.Sensor in /info?module=Ventilation response",
            id="sensor_not_object",
        ),
        pytest.param(
            {"Ventilation": {"Sensor": {"TempOda": 175}}},
            "Expected wrapped Val object for Ventilation.Sensor.TempOda, got int",
            id="leaf_not_object",
        ),
        pytest.param(
            {"Ventilation": {"Sensor": {"TempOda": {"Val": "175"}}}},
            "Expected integer value for Ventilation.Sensor.TempOda, got str",
            id="leaf_non_int_val",
        ),
    ],
)
async def test_get_ventilation_temperature_info_rejects_malformed_payloads(
    payload: object,
    message: str,
) -> None:
    """Malformed ventilation temperature payloads should raise DucoError."""
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoError, match=re.escape(message)),
        ):
            await client.async_get_ventilation_temperature_info()


async def test_get_bypass_supply_temperature_target_returns_converted_values(
    config_data: dict[str, object],
) -> None:
    """Bypass target helpers should convert raw config metadata to Celsius."""
    mock_response = _response(json_payload=config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            payload = await client.async_get_bypass_supply_temperature_target(1)

    assert payload == BypassSupplyTemperatureTarget(
        zone_id=1,
        value=18.0,
        minimum=12.0,
        increment=0.5,
        maximum=22.0,
    )
    assert request_mock.call_args.kwargs["params"] == {
        "module": "HeatRecovery",
        "submodule": "Bypass",
        "parameter": "TempSupTgtZone1",
    }


async def test_get_bypass_supply_temperature_targets_returns_available_targets(
    config_data: dict[str, object],
) -> None:
    """Bulk bypass target reads should return all available targets in Celsius."""
    mock_response = _response(json_payload=config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request_mock = _request(mock_response)
        with patch.object(session, "request", request_mock):
            targets = await client.async_get_bypass_supply_temperature_targets()

    assert targets == {
        1: BypassSupplyTemperatureTarget(
            zone_id=1,
            value=18.0,
            minimum=12.0,
            increment=0.5,
            maximum=22.0,
        ),
        2: BypassSupplyTemperatureTarget(
            zone_id=2,
            value=18.5,
            minimum=12.0,
            increment=0.5,
            maximum=22.0,
        ),
    }
    assert request_mock.call_args.kwargs["params"] == {
        "module": "HeatRecovery",
        "submodule": "Bypass",
    }


async def test_get_bypass_supply_temperature_targets_returns_empty_when_absent() -> None:
    """Bulk bypass target reads should omit targets absent from the response."""
    mock_response = _response(json_payload={"HeatRecovery": {"Bypass": {}}})

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            targets = await client.async_get_bypass_supply_temperature_targets()

    assert targets == {}


async def test_get_bypass_supply_temperature_targets_raises_when_unsupported() -> None:
    """Unsupported bulk bypass target reads should raise a typed capability error."""
    mock_response = _response(
        status=400,
        text_payload='{"Code":3,"Result":"FAILED"}',
    )

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoUnsupportedCapabilityError),
        ):
            await client.async_get_bypass_supply_temperature_targets()


async def test_get_bypass_supply_temperature_targets_reraises_other_client_errors() -> None:
    """Unexpected bulk bypass target failures should remain visible to callers."""
    mock_response = _response(status=400, text_payload='{"Code":4,"Result":"FAILED"}')

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoResponseError),
        ):
            await client.async_get_bypass_supply_temperature_targets()


async def test_get_bypass_supply_temperature_target_raises_when_not_reported() -> None:
    """Missing bypass targets should fail for parameter-specific helper reads."""
    mock_response = _response(json_payload={"HeatRecovery": {"Bypass": {}}})

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match=re.escape("Expected TempSupTgtZone1 in /config response"),
            ),
        ):
            await client.async_get_bypass_supply_temperature_target(1)


async def test_get_bypass_supply_temperature_target_raises_when_unsupported() -> None:
    """Unsupported bypass targets should raise a typed capability error."""
    mock_response = _response(
        status=400,
        text_payload='{"Code":3,"Result":"FAILED"}',
    )

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoUnsupportedCapabilityError) as err_info,
        ):
            await client.async_get_bypass_supply_temperature_target(1)

    assert err_info.value.status == 400
    assert err_info.value.path == "/config"


async def test_get_bypass_supply_temperature_target_reraises_other_client_errors() -> None:
    """Unexpected bypass target failures should remain visible to callers."""
    mock_response = _response(status=400, text_payload='{"Code":4,"Result":"FAILED"}')

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoResponseError),
        ):
            await client.async_get_bypass_supply_temperature_target(1)


@pytest.mark.parametrize("zone_id", [0, 9, "1"])
async def test_bypass_supply_temperature_helpers_reject_invalid_zone_ids(zone_id: object) -> None:
    """Bypass target helpers should validate the supported zone range."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with pytest.raises(ValueError, match="zone_id must be an integer between 1 and 8"):
            await client.async_get_bypass_supply_temperature_target(cast(Any, zone_id))

        with pytest.raises(ValueError, match="zone_id must be an integer between 1 and 8"):
            await client.async_set_bypass_supply_temperature_target(cast(Any, zone_id), 18.0)


async def test_set_bypass_supply_temperature_target_serializes_decicelsius(
    config_data: dict[str, object],
) -> None:
    """Bypass target helpers should serialize Celsius writes as raw decicelsius values."""
    mock_response = _response(json_payload=config_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            payload = await client.async_set_bypass_supply_temperature_target(2, 18.5)

    assert payload == BypassSupplyTemperatureTarget(
        zone_id=2,
        value=18.5,
        minimum=12.0,
        increment=0.5,
        maximum=22.0,
    )
    _, kwargs = request.call_args
    assert kwargs["params"] == {
        "module": "HeatRecovery",
        "submodule": "Bypass",
        "parameter": "TempSupTgtZone2",
    }
    assert kwargs["data"] == b'{"HeatRecovery":{"Bypass":{"TempSupTgtZone2":{"Val":185}}}}'
    assert kwargs["headers"] == {"Content-Type": "application/json"}


@pytest.mark.parametrize(
    ("value", "message"),
    [
        pytest.param(18.34, "must be representable in 0.1°C increments", id="not_decicelsius"),
        pytest.param(float("inf"), "must be a finite temperature value", id="not_finite"),
        pytest.param(True, "must be an int or float, got bool", id="bool"),
    ],
)
async def test_set_bypass_supply_temperature_target_rejects_invalid_temperatures(
    value: object,
    message: str,
) -> None:
    """Invalid convenience write values should fail before a request is sent."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with pytest.raises(ValueError, match=re.escape(message)):
            await client.async_set_bypass_supply_temperature_target(1, cast(Any, value))


async def test_get_write_requests_remaining_is_parsed() -> None:
    """Test parsing of the remaining write budget."""
    payload: dict[str, object] = {"General": {"PublicApi": {"WriteReqCntRemain": {"Val": 197}}}}
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            remaining = await client.async_get_write_requests_remaining()

    assert remaining == 197


async def test_get_time_filter_remaining_is_parsed() -> None:
    """Heat recovery filter time should be parsed when the box reports it."""
    payload: dict[str, object] = {"HeatRecovery": {"General": {"TimeFilterRemain": {"Val": 180}}}}
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            remaining = await client.async_get_time_filter_remaining()

    assert remaining == 180


async def test_get_time_filter_remaining_returns_none_when_not_reported() -> None:
    """Heat recovery filter time should stay optional for boxes that omit it."""
    payload: dict[str, object] = {"HeatRecovery": {"General": {}}}
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            remaining = await client.async_get_time_filter_remaining()

    assert remaining is None


async def test_get_time_filter_remaining_returns_none_for_unsupported_module() -> None:
    """Unsupported heat recovery modules should remain an optional value."""
    mock_response = _response(
        status=400,
        text_payload='{"Code":3,"Result":"FAILED"}',
    )

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            remaining = await client.async_get_time_filter_remaining()

    assert remaining is None


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        pytest.param(
            [],
            "Expected object payload from /info?module=HeatRecovery, got list",
            id="root_not_object",
        ),
        pytest.param(
            {"HeatRecovery": []},
            "Expected object payload at HeatRecovery in /info?module=HeatRecovery response",
            id="heat_recovery_not_object",
        ),
        pytest.param(
            {"HeatRecovery": {"General": []}},
            "Expected object payload at HeatRecovery.General in /info?module=HeatRecovery response",
            id="general_not_object",
        ),
        pytest.param(
            {"HeatRecovery": {"General": {"TimeFilterRemain": 180}}},
            "Expected wrapped Val object for HeatRecovery.General.TimeFilterRemain, got int",
            id="leaf_not_object",
        ),
        pytest.param(
            {"HeatRecovery": {"General": {"TimeFilterRemain": None}}},
            "Expected wrapped Val object for HeatRecovery.General.TimeFilterRemain, got NoneType",
            id="leaf_null",
        ),
        pytest.param(
            {"HeatRecovery": {"General": {"TimeFilterRemain": {}}}},
            "Expected wrapped Val object for HeatRecovery.General.TimeFilterRemain",
            id="leaf_missing_val",
        ),
        pytest.param(
            {"HeatRecovery": {"General": {"TimeFilterRemain": {"Val": "180"}}}},
            "Expected integer value for HeatRecovery.General.TimeFilterRemain, got str",
            id="leaf_non_int_val",
        ),
    ],
)
async def test_get_time_filter_remaining_rejects_malformed_payloads(
    payload: object,
    message: str,
) -> None:
    """Malformed heat recovery payloads should raise DucoError."""
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoError, match=re.escape(message)),
        ):
            await client.async_get_time_filter_remaining()


async def test_get_write_req_remaining_alias_is_parsed() -> None:
    """The old write budget method name should remain available."""
    payload: dict[str, object] = {"General": {"PublicApi": {"WriteReqCntRemain": {"Val": 197}}}}
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            remaining = await client.async_get_write_req_remaining()

    assert remaining == 197


async def test_get_write_req_remaining_alias_logs_external_caller(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Compatibility logging should include the external caller path."""
    payload: dict[str, object] = {"General": {"PublicApi": {"WriteReqCntRemain": {"Val": 197}}}}
    mock_response = _response(json_payload=payload)

    async def external_wrapper(client: DucoClient) -> int:
        return await client.async_get_write_req_remaining()

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            caplog.at_level(logging.DEBUG, logger="duco_connectivity.client"),
            patch.object(session, "request", _request(mock_response)),
        ):
            remaining = await external_wrapper(client)

    assert remaining == 197
    assert (
        "Compatibility alias async_get_write_req_remaining() used by "
        "test_client.external_wrapper; delegating to "
        "async_get_write_requests_remaining()."
    ) in caplog.text


async def test_get_write_req_remaining_alias_treats_prefixed_external_module_as_external(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Modules like duco_connectivity_tools should not be treated as internal."""
    payload: dict[str, object] = {"General": {"PublicApi": {"WriteReqCntRemain": {"Val": 197}}}}
    mock_response = _response(json_payload=payload)
    external_wrapper = _build_async_wrapper(
        "duco_connectivity_tools",
        "async def external_wrapper(client):\n"
        "    return await client.async_get_write_req_remaining()\n",
    )

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            caplog.at_level(logging.DEBUG, logger="duco_connectivity.client"),
            patch.object(session, "request", _request(mock_response)),
        ):
            remaining = await external_wrapper(client)

    assert remaining == 197
    assert (
        "Compatibility alias async_get_write_req_remaining() used by "
        "duco_connectivity_tools.external_wrapper; delegating to "
        "async_get_write_requests_remaining()."
    ) in caplog.text


async def test_get_write_req_remaining_alias_logs_compat_usage(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The compatibility alias should emit a debug log when it is used."""
    payload: dict[str, object] = {"General": {"PublicApi": {"WriteReqCntRemain": {"Val": 197}}}}
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            caplog.at_level(logging.DEBUG, logger="duco_connectivity.client"),
            patch.object(session, "request", _request(mock_response)),
        ):
            await client.async_get_write_req_remaining()

    assert "Compatibility alias async_get_write_req_remaining() used" in caplog.text


@pytest.mark.parametrize(
    ("raw_state", "mode", "expected_state"),
    [
        ("MAN3x2", "MANU", VentilationState.MAN3x2),
        ("-", "AUTO", VentilationState.NONE),
    ],
)
async def test_known_ventilation_state_is_parsed(
    raw_state: str,
    mode: str,
    expected_state: VentilationState,
) -> None:
    """Documented and compatibility ventilation states should parse without fallback."""
    payload: dict[str, object] = {
        "Nodes": [
            {
                "Node": 1,
                "General": {
                    "Type": {"Val": "BOX"},
                    "SubType": {"Val": 1},
                    "NetworkType": {"Val": "VIRT"},
                    "Parent": {"Val": 0},
                    "Asso": {"Val": 0},
                    "Name": {"Val": "Living"},
                    "Identify": {"Val": 0},
                },
                "Ventilation": {
                    "State": {"Val": raw_state},
                    "Mode": {"Val": mode},
                    "TimeStateRemain": {"Val": 1200},
                    "TimeStateEnd": {"Val": 1778269000},
                    "FlowLvlTgt": {"Val": 100},
                },
            }
        ]
    }

    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            nodes = await client.async_get_nodes()

    assert len(nodes) == 1
    assert nodes[0].ventilation is not None
    assert nodes[0].ventilation.state is expected_state


@pytest.mark.parametrize(
    ("raw_mode", "expected_mode"),
    [
        ("-", VentilationMode.NONE),
        ("AUTO", VentilationMode.AUTO),
        ("MANU", VentilationMode.MANU),
        ("OVRL", VentilationMode.OVRL),
        ("EXTN", VentilationMode.EXTN),
        ("COOL", VentilationMode.COOL),
        ("N/A", VentilationMode.NA),
        ("DSBL", VentilationMode.DSBL),
    ],
)
async def test_known_ventilation_mode_is_parsed(
    raw_mode: str,
    expected_mode: VentilationMode,
) -> None:
    """Documented ventilation modes should parse without fallback."""
    payload: dict[str, object] = {
        "Nodes": [
            {
                "Node": 7,
                "General": {
                    "Type": {"Val": "BOX"},
                    "SubType": {"Val": 1},
                    "NetworkType": {"Val": "VIRT"},
                    "Parent": {"Val": 0},
                    "Asso": {"Val": 0},
                    "Name": {"Val": "Bedroom"},
                    "Identify": {"Val": 0},
                },
                "Ventilation": {
                    "State": {"Val": "AUTO"},
                    "Mode": {"Val": raw_mode},
                    "TimeStateRemain": {"Val": 0},
                    "TimeStateEnd": {"Val": 0},
                },
            }
        ]
    }

    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            nodes = await client.async_get_nodes()

    assert len(nodes) == 1
    assert nodes[0].ventilation is not None
    assert nodes[0].ventilation.mode is expected_mode


async def test_get_nodes_unknown_ventilation_state_falls_back_to_unknown() -> None:
    """Unknown ventilation states should not break node parsing."""
    payload: dict[str, object] = {
        "Nodes": [
            {
                "Node": 6,
                "General": {
                    "Type": {"Val": "BOX"},
                    "SubType": {"Val": 1},
                    "NetworkType": {"Val": "VIRT"},
                    "Parent": {"Val": 0},
                    "Asso": {"Val": 0},
                    "Name": {"Val": "Living"},
                    "Identify": {"Val": 0},
                },
                "Ventilation": {
                    "State": {"Val": "FUTURE_STATE"},
                    "Mode": {"Val": "AUTO"},
                    "TimeStateRemain": {"Val": 0},
                    "TimeStateEnd": {"Val": 0},
                },
            }
        ]
    }

    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            nodes = await client.async_get_nodes()

    assert len(nodes) == 1
    assert nodes[0].ventilation is not None
    assert nodes[0].ventilation.state is VentilationState.UNKNOWN


async def test_get_nodes_unknown_ventilation_mode_falls_back_to_unknown() -> None:
    """Unknown ventilation modes should not break node parsing."""
    payload: dict[str, object] = {
        "Nodes": [
            {
                "Node": 7,
                "General": {
                    "Type": {"Val": "BOX"},
                    "SubType": {"Val": 1},
                    "NetworkType": {"Val": "VIRT"},
                    "Parent": {"Val": 0},
                    "Asso": {"Val": 0},
                    "Name": {"Val": "Bedroom"},
                    "Identify": {"Val": 0},
                },
                "Ventilation": {
                    "State": {"Val": "AUTO"},
                    "Mode": {"Val": "FUTURE_MODE"},
                    "TimeStateRemain": {"Val": 0},
                    "TimeStateEnd": {"Val": 0},
                },
            }
        ]
    }

    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            nodes = await client.async_get_nodes()

    assert len(nodes) == 1
    assert nodes[0].ventilation is not None
    assert nodes[0].ventilation.mode is VentilationMode.UNKNOWN


async def test_connection_error_raises_duco_connection_error() -> None:
    """Transport errors should raise DucoConnectionError."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(
            session,
            "request",
            MagicMock(side_effect=aiohttp.ClientConnectionError("unreachable")),
        ):
            with pytest.raises(DucoConnectionError, match="Could not reach Duco device"):
                await client.async_get_api_info()


async def test_timeout_raises_duco_connection_error() -> None:
    """Timeouts should surface as DucoConnectionError."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", MagicMock(side_effect=TimeoutError())):
            with pytest.raises(DucoConnectionError, match="Could not reach Duco device"):
                await client.async_get_api_info()


async def test_http_error_raises_duco_response_error() -> None:
    """HTTP >= 400 should raise DucoResponseError with HTTP metadata."""
    mock_response = _response(status=500, json_payload={}, text_payload="boom")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            with pytest.raises(
                DucoResponseError,
                match="Unexpected response 500 for /api: boom",
            ) as err_info:
                await client.async_get_api_info()

    err = err_info.value
    assert isinstance(err, DucoError)
    assert err.status == 500
    assert err.path == "/api"
    assert err.body == "boom"


async def test_invalid_json_raises_duco_error(api_info_data: dict[str, object]) -> None:
    """Non-JSON responses should raise DucoError."""
    del api_info_data
    mock_response = _response(
        status=200,
        json_side_effect=ValueError("not json"),
        text_payload="<html>oops</html>",
    )

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            with pytest.raises(DucoError, match="Expected JSON response"):
                await client.async_get_api_info()


async def test_write_limit_error_is_raised() -> None:
    """HTTP 429 should raise DucoWriteLimitError."""
    mock_response = _response(status=429, json_payload={})
    request_context = _request_context(mock_response)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", MagicMock(return_value=request_context)):
            with pytest.raises(
                DucoWriteLimitError,
                match="Duco write capacity exhausted",
            ) as err_info:
                await client.async_set_ventilation_state(1, "MAN2")

    request_context.__aexit__.assert_awaited_once()
    err = err_info.value
    assert isinstance(err, DucoError)
    assert err.status == 429
    assert err.path == "/action/nodes/1"
    assert err.body == ""


async def test_get_actions_returns_typed_items(
    action_items_data: list[dict[str, object]],
) -> None:
    """System action discovery should parse the bare ActionItemList payload."""
    mock_response = _response(json_payload=action_items_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            result = await client.async_get_actions()

    assert result == [
        ActionItem(action="SetIdentify", val_type=ActionValueType.NONE),
        ActionItem(
            action="SetWifiApMode",
            val_type=ActionValueType.ENUM,
            enum_values=["Off", "On"],
        ),
    ]
    assert request.call_args.args[:2] == ("GET", "http://192.0.2.94/action")
    assert result[0].raw_payload is action_items_data[0]
    assert isinstance(result[0].action, ActionName)
    assert isinstance(result[1].enum_values[0], ActionEnumValue)


async def test_get_actions_unknown_val_type_falls_back_to_unknown() -> None:
    """Unknown action discovery value kinds should fall back to UNKNOWN."""
    mock_response = _response(
        json_payload=[
            {
                "Action": "SetFutureAction",
                "ValType": "FutureType",
            }
        ]
    )

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            result = await client.async_get_actions()

    assert result == [ActionItem(action="SetFutureAction", val_type=ActionValueType.UNKNOWN)]
    assert isinstance(result[0].action, ActionName)
    assert result[0].action.known_value is None


async def test_get_actions_preserves_forward_compatible_enum_options() -> None:
    """Action discovery should keep future action names and enum options usable."""
    payload: list[dict[str, object]] = [
        {
            "Action": "SetFutureAction",
            "ValType": "Enum",
            "Enum": ["FutureOff", "FutureOn"],
        }
    ]
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            result = await client.async_get_actions()

    assert result[0].action == "SetFutureAction"
    assert result[0].action.known_value is None
    assert result[0].enum_values == ["FutureOff", "FutureOn"]
    assert all(isinstance(value, ActionEnumValue) for value in result[0].enum_values)


@pytest.mark.parametrize(
    ("payload", "message"),
    ACTION_DISCOVERY_MALFORMED_PAYLOADS,
)
async def test_get_actions_rejects_malformed_payloads(
    payload: object,
    message: str,
) -> None:
    """Malformed system action discovery payloads should raise DucoError."""
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoError, match=re.escape(message)),
        ):
            await client.async_get_actions()


async def test_get_actions_api_error_raises_duco_error() -> None:
    """HTTP errors from action discovery should surface as DucoError."""
    mock_response = _response(status=404, text_payload="action endpoint missing")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match="Unexpected response 404 for /action: action endpoint missing",
            ),
        ):
            await client.async_get_actions()


async def test_get_actions_connection_error_raises_duco_connection_error() -> None:
    """Transport failures from action discovery should surface as connection errors."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(
                session,
                "request",
                MagicMock(side_effect=aiohttp.ClientError("boom")),
            ),
            pytest.raises(DucoConnectionError, match="Could not reach Duco device"),
        ):
            await client.async_get_actions()


async def test_get_node_actions_returns_typed_items(
    node_action_items_data: dict[str, object],
) -> None:
    """Node action discovery should parse the nested NodeListActionItemList payload."""
    mock_response = _response(json_payload=node_action_items_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            result = await client.async_get_node_actions()

    assert result == NodeListActionItemList(
        nodes=[
            NodeActionItemList(
                node_id=1,
                actions=[ActionItem(action="SetIdentify", val_type=ActionValueType.NONE)],
            ),
            NodeActionItemList(
                node_id=7,
                actions=[
                    ActionItem(
                        action="SetVentilationState",
                        val_type=ActionValueType.ENUM,
                        enum_values=["AUTO", "MAN1", "MAN2", "MAN3"],
                    )
                ],
            ),
            NodeActionItemList(node_id=113),
        ]
    )
    assert request.call_args.args[:2] == ("GET", "http://192.0.2.94/action/nodes")
    assert result.raw_payload is node_action_items_data
    assert result.nodes[0].raw_payload is node_action_items_data["Nodes"][0]
    assert isinstance(result.nodes[0].actions[0].action, ActionName)
    assert isinstance(result.nodes[1].actions[0].enum_values[0], ActionEnumValue)


@pytest.mark.parametrize(
    ("payload", "message"),
    NODE_ACTION_DISCOVERY_MALFORMED_PAYLOADS,
)
async def test_get_node_actions_rejects_malformed_payloads(
    payload: object,
    message: str,
) -> None:
    """Malformed node action discovery payloads should raise DucoError."""
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoError, match=re.escape(message)),
        ):
            await client.async_get_node_actions()


async def test_get_node_actions_api_error_raises_duco_error() -> None:
    """HTTP errors from node action discovery should surface as DucoError."""
    mock_response = _response(status=404, text_payload="node action endpoint missing")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match="Unexpected response 404 for /action/nodes: node action endpoint missing",
            ),
        ):
            await client.async_get_node_actions()


async def test_get_node_actions_connection_error_raises_duco_connection_error() -> None:
    """Transport failures from node action discovery should surface as connection errors."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(
                session,
                "request",
                MagicMock(side_effect=aiohttp.ClientError("boom")),
            ),
            pytest.raises(DucoConnectionError, match="Could not reach Duco device"),
        ):
            await client.async_get_node_actions()


async def test_get_node_actions_for_node_returns_typed_items(
    node_action_item_data: dict[str, object],
) -> None:
    """Per-node action discovery should parse the NodeActionItemList payload."""
    mock_response = _response(json_payload=node_action_item_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            result = await client.async_get_node_actions_for_node(7)

    assert result == NodeActionItemList(
        node_id=7,
        actions=[
            ActionItem(
                action="SetVentilationState",
                val_type=ActionValueType.ENUM,
                enum_values=["AUTO", "MAN1", "MAN2", "MAN3"],
            )
        ],
    )
    assert request.call_args.args[:2] == ("GET", "http://192.0.2.94/action/nodes/7")
    assert result.raw_payload is node_action_item_data
    assert isinstance(result.actions[0].action, ActionName)
    assert isinstance(result.actions[0].enum_values[0], ActionEnumValue)


@pytest.mark.parametrize(
    ("payload", "message"),
    NODE_ACTION_DISCOVERY_FOR_NODE_MALFORMED_PAYLOADS,
)
async def test_get_node_actions_for_node_rejects_malformed_payloads(
    payload: object,
    message: str,
) -> None:
    """Malformed per-node action discovery payloads should raise DucoError."""
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(DucoError, match=re.escape(message)),
        ):
            await client.async_get_node_actions_for_node(7)


async def test_get_node_actions_for_node_api_error_raises_duco_error() -> None:
    """HTTP errors from per-node action discovery should surface as DucoError."""
    mock_response = _response(status=404, text_payload="node not found")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match="Unexpected response 404 for /action/nodes/7: node not found",
            ),
        ):
            await client.async_get_node_actions_for_node(7)


async def test_get_node_actions_for_node_connection_error_raises_duco_connection_error() -> None:
    """Transport failures from per-node action discovery should surface as connection errors."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(
                session,
                "request",
                MagicMock(side_effect=aiohttp.ClientError("boom")),
            ),
            pytest.raises(DucoConnectionError, match="Could not reach Duco device"),
        ):
            await client.async_get_node_actions_for_node(7)


async def test_set_action_returns_typed_result(
    action_result_success_data: dict[str, object],
) -> None:
    """Generic system actions should parse a typed action result."""
    mock_response = _response(json_payload=action_result_success_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            result = await client.async_set_action(ActionName("SetWifiApMode"), "On")

    assert result.result is ActionResultStatus.SUCCESS
    assert result.code is None
    assert result.message is None
    assert result.raw_payload is action_result_success_data
    assert request.call_args.args[:2] == ("POST", "http://192.0.2.94/action")
    _, kwargs = request.call_args
    assert kwargs["data"] == b'{"Action":"SetWifiApMode","Val":"On"}'
    assert kwargs["headers"] == {"Content-Type": "application/json"}


async def test_set_action_omits_optional_value(
    action_result_success_data: dict[str, object],
) -> None:
    """Generic system actions should omit Val when the action does not require one."""
    mock_response = _response(json_payload=action_result_success_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            await client.async_set_action("SetIdentify")

    _, kwargs = request.call_args
    assert kwargs["data"] == b'{"Action":"SetIdentify"}'
    assert kwargs["headers"] == {"Content-Type": "application/json"}


async def test_set_action_returns_failed_result(
    action_result_failed_data: dict[str, object],
) -> None:
    """Generic system actions should preserve FAILED action responses."""
    mock_response = _response(json_payload=action_result_failed_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            result = await client.async_set_action("SetWifiApMode", "Off")

    assert result.result is ActionResultStatus.FAILED
    assert result.code == 12
    assert result.message == "Action is not performed"


async def test_set_action_returns_unknown_result_for_unmapped_status() -> None:
    """Unknown system action result values should fall back to ActionResultStatus.UNKNOWN."""
    mock_response = _response(
        json_payload={
            "Result": {"Val": "FUTURE_RESULT"},
            "Code": {"Val": 7},
        }
    )

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            result = await client.async_set_action("SetIdentify")

    assert result.result is ActionResultStatus.UNKNOWN
    assert result.code == 7
    assert result.message is None


async def test_set_action_invalid_result_raises_duco_error() -> None:
    """Malformed system action responses should raise DucoError."""
    mock_response = _response(json_payload={"Code": 12})

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            with pytest.raises(DucoError, match="Expected Result in system action response"):
                await client.async_set_action("SetIdentify")


async def test_set_action_api_error_raises_duco_error() -> None:
    """HTTP errors from system action execution should surface as DucoError."""
    mock_response = _response(status=404, text_payload="action endpoint missing")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match="Unexpected response 404 for /action: action endpoint missing",
            ),
        ):
            await client.async_set_action("SetIdentify")


async def test_set_action_connection_error_raises_duco_connection_error() -> None:
    """Transport failures from system action execution should surface as connection errors."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(
                session,
                "request",
                MagicMock(side_effect=aiohttp.ClientError("boom")),
            ),
            pytest.raises(DucoConnectionError, match="Could not reach Duco device"),
        ):
            await client.async_set_action("SetIdentify")


async def test_set_node_action_returns_typed_result(
    action_result_success_data: dict[str, object],
) -> None:
    """Generic node actions should parse a typed action result."""
    mock_response = _response(json_payload=action_result_success_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            result = await client.async_set_node_action(
                1,
                ActionName("SetVentilationState"),
                "MAN2",
            )

    assert result.result is ActionResultStatus.SUCCESS
    assert result.code is None
    assert result.message is None
    _, kwargs = request.call_args
    assert kwargs["data"] == b'{"Action":"SetVentilationState","Val":"MAN2"}'
    assert kwargs["headers"] == {"Content-Type": "application/json"}


async def test_set_node_action_omits_optional_value(
    action_result_success_data: dict[str, object],
) -> None:
    """Generic node actions should omit Val when the action does not require one."""
    mock_response = _response(json_payload=action_result_success_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            await client.async_set_node_action(1, "SetIdentify")

    _, kwargs = request.call_args
    assert kwargs["data"] == b'{"Action":"SetIdentify"}'
    assert kwargs["headers"] == {"Content-Type": "application/json"}


async def test_set_node_action_returns_failed_result(
    action_result_failed_data: dict[str, object],
) -> None:
    """Generic node actions should preserve FAILED action responses."""
    mock_response = _response(json_payload=action_result_failed_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            result = await client.async_set_node_action(1, "SetPosMan", 2)

    assert result.result is ActionResultStatus.FAILED
    assert result.code == 12
    assert result.message == "Action is not performed"


async def test_set_node_action_returns_unknown_result_for_unmapped_status() -> None:
    """Unknown action result values should fall back to ActionResultStatus.UNKNOWN."""
    mock_response = _response(
        json_payload={
            "Result": {"Val": "FUTURE_RESULT"},
            "Code": {"Val": 7},
        }
    )

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            result = await client.async_set_node_action(1, "SetIdentify")

    assert result.result is ActionResultStatus.UNKNOWN
    assert result.code == 7
    assert result.message is None


async def test_set_node_action_invalid_result_raises_duco_error() -> None:
    """Malformed node action responses should raise DucoError."""
    mock_response = _response(json_payload={"Code": 12})

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            with pytest.raises(DucoError, match="Expected Result in node action response"):
                await client.async_set_node_action(1, "SetIdentify")


async def test_set_ventilation_state_delegates_to_generic_node_action() -> None:
    """Ventilation writes should remain a thin wrapper over the generic node action path."""
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(client, "async_set_node_action", AsyncMock()) as set_node_action:
            await client.async_set_ventilation_state(1, VentilationState.MAN2)

    set_node_action.assert_awaited_once_with(
        node_id=1,
        action="SetVentilationState",
        val="MAN2",
    )


async def test_set_ventilation_state_uses_compact_json_body() -> None:
    """Write requests should use compact JSON with explicit content type."""
    mock_response = _response(json_payload={"Result": "SUCCESS"})

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            await client.async_set_ventilation_state(1, "MAN2")

    _, kwargs = request.call_args
    assert kwargs["data"] == b'{"Action":"SetVentilationState","Val":"MAN2"}'
    assert kwargs["headers"] == {"Content-Type": "application/json"}
