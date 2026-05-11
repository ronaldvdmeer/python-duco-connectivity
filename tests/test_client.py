"""Tests for the HTTP-only Duco connectivity client."""

import logging
import re
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from duco_connectivity import (
    ActionItem,
    ActionResultStatus,
    ActionValueType,
    Config,
    ConfigNode,
    ConfigNodeOverview,
    ConfigNodeStruct,
    ConfigSection,
    ConfigValue,
    ConfigValueOptions,
    ConfigValueString,
    DiagStatus,
    DucoClient,
    DucoConnectionError,
    DucoError,
    DucoWriteLimitError,
    NetworkType,
    NodeActionItemList,
    NodeListActionItemList,
    NodeOverview,
    NodeType,
    PatchConfigNodeValue,
    PatchConfigValue,
    VentilationMode,
    VentilationState,
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

    assert api_info.public_api_version == "2.6"
    assert api_info.reported_api_version == "MOCKAPI 2.6.0"
    assert len(api_info.endpoints) == 2
    assert api_info.endpoints[1].url == "/info"
    assert api_info.endpoints[1].query_parameters == [
        "module",
        "submodule",
        "parameter",
    ]


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
    patch_value = PatchConfigValue(value=2)
    patch_node_value = PatchConfigNodeValue(value="Boost")

    assert node_struct.name is name
    assert node.node_id == 7
    assert node.name is name
    assert overview.nodes == [node]
    assert patch_value.value == 2
    assert patch_node_value.value == "Boost"


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


async def test_set_config_invalid_response_raises_duco_error() -> None:
    """Malformed config PATCH responses should raise DucoError."""
    mock_response = _response(json_payload={"General": {"Lan": {"Mode": {"Val": False}}}})

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with (
            patch.object(session, "request", _request(mock_response)),
            pytest.raises(
                DucoError,
                match="Unsupported config value type bool for General.Lan.Mode",
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
                match="Expected string Val for node config value /config/nodes/7.Name, got int",
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

    assert board.box_name == "SILENT_CONNECT"
    assert board.box_sub_type_name == "Eu"
    assert board.serial_board_box == "RS0000000001"
    assert board.time == 1775082497
    assert board.public_api_version == "2.5"
    assert board.software_version is None


async def test_board_info_with_optional_versions(
    board_info_with_optional_versions_data: dict[str, object],
) -> None:
    """Test board info parsing with SwVersion."""
    mock_response = _response(json_payload=board_info_with_optional_versions_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            board = await client.async_get_board_info()

    assert board.public_api_version == "2.6"
    assert board.software_version == "2.0.6.0"


async def test_lan_info_wifi_is_parsed(lan_info_data: dict[str, object]) -> None:
    """Test LAN parsing for Wi-Fi connected boxes."""
    mock_response = _response(json_payload=lan_info_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            lan = await client.async_get_lan_info()

    assert lan.mode == "WIFI_CLIENT"
    assert lan.ip == "192.0.2.94"
    assert lan.rssi_wifi == -44


async def test_lan_info_ethernet_is_parsed(
    lan_info_ethernet_data: dict[str, object],
) -> None:
    """Test LAN parsing for ethernet connected boxes."""
    mock_response = _response(json_payload=lan_info_ethernet_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            lan = await client.async_get_lan_info()

    assert lan.mode == "ETHERNET"
    assert lan.ip == "198.51.100.97"
    assert lan.rssi_wifi is None


async def test_get_diagnostics(diag_data: dict[str, object]) -> None:
    """Test diagnostics parsing."""
    mock_response = _response(json_payload=diag_data)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            diags = await client.async_get_diagnostics()

    assert len(diags) == 3
    assert diags[0].component == "Ventilation"
    assert diags[0].status == DiagStatus.OK


async def test_get_diagnostics_unknown_status_falls_back_to_unknown() -> None:
    """Unknown diagnostic statuses should not break parsing."""
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
    assert diags[0].status == DiagStatus.UNKNOWN


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
    assert box.general.network_type == NetworkType.VIRT
    assert box.ventilation is not None
    assert box.ventilation.state == VentilationState.CNT1
    assert box.ventilation.flow_lvl_tgt == 15
    assert box.sensor is not None
    assert box.sensor.rh == 35.5
    assert box.sensor.iaq_rh == 83
    assert box.sensor.co2 is None
    assert box.sensor.temp == 27.9

    ucco2 = nodes[1]
    assert ucco2.general.node_type == NodeType.UCCO2
    assert ucco2.general.network_type == NetworkType.RF
    assert ucco2.sensor is not None
    assert ucco2.sensor.co2 == 536
    assert ucco2.sensor.iaq_co2 == 100


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
    assert node.sensor is not None
    assert node.sensor.co2 == 536
    assert node.sensor.iaq_co2 == 100


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


async def test_get_nodes_mb_network_type_is_parsed() -> None:
    """Known MB network types should be parsed explicitly."""
    payload: dict[str, object] = {
        "Nodes": [
            {
                "Node": 4,
                "General": {
                    "Type": {"Val": "UCCO2"},
                    "SubType": {"Val": 0},
                    "NetworkType": {"Val": "MB"},
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
    assert nodes[0].general.network_type == NetworkType.MB


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


async def test_get_write_requests_remaining_is_parsed() -> None:
    """Test parsing of the remaining write budget."""
    payload: dict[str, object] = {"General": {"PublicApi": {"WriteReqCntRemain": {"Val": 197}}}}
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            remaining = await client.async_get_write_requests_remaining()

    assert remaining == 197


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


async def test_http_error_raises_duco_error() -> None:
    """HTTP >= 400 should raise DucoError."""
    mock_response = _response(status=500, json_payload={}, text_payload="boom")

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            with pytest.raises(DucoError, match="Unexpected response 500"):
                await client.async_get_api_info()


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
            with pytest.raises(DucoWriteLimitError, match="Duco write capacity exhausted"):
                await client.async_set_ventilation_state(1, "MAN2")

    request_context.__aexit__.assert_awaited_once()


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
            result = await client.async_set_action("SetWifiApMode", "On")

    assert result.result is ActionResultStatus.SUCCESS
    assert result.code is None
    assert result.message is None
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
            result = await client.async_set_node_action(1, "SetVentilationState", "MAN2")

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
