"""Tests for the HTTP-only Duco connectivity client."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from duco_connectivity import (
    DiagStatus,
    DucoClient,
    DucoConnectionError,
    DucoError,
    DucoWriteLimitError,
    NetworkType,
    NodeType,
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
    assert api_info.endpoints[1].query_parameters == ["module", "submodule", "parameter"]


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


async def test_get_write_requests_remaining_is_parsed() -> None:
    """Test parsing of the remaining write budget."""
    payload: dict[str, object] = {"General": {"PublicApi": {"WriteReqCntRemain": {"Val": 197}}}}
    mock_response = _response(json_payload=payload)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        with patch.object(session, "request", _request(mock_response)):
            remaining = await client.async_get_write_requests_remaining()

    assert remaining == 197


async def test_timed_manual_state_is_parsed() -> None:
    """Test that timed manual ventilation states are accepted from the API."""
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
                    "State": {"Val": "MAN3x2"},
                    "Mode": {"Val": "MANU"},
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
    assert nodes[0].ventilation.state is VentilationState.MAN3x2


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


async def test_set_ventilation_state_uses_compact_json_body() -> None:
    """Write requests should use compact JSON with explicit content type."""
    mock_response = _response(json_payload={})

    async with aiohttp.ClientSession() as session:
        client = DucoClient(session=session, host="192.0.2.94")
        request = MagicMock(return_value=_request_context(mock_response))
        with patch.object(session, "request", request):
            await client.async_set_ventilation_state(1, "MAN2")

    _, kwargs = request.call_args
    assert kwargs["data"] == b'{"Action":"SetVentilationState","Val":"MAN2"}'
    assert kwargs["headers"] == {"Content-Type": "application/json"}
