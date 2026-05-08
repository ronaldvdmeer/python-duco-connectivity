"""Async client for the local Duco HTTP API."""

import json
from typing import Any
from urllib.parse import urlsplit

import aiohttp

from .exceptions import DucoConnectionError, DucoError, DucoWriteLimitError
from .models import (
    ApiEndpoint,
    ApiInfo,
    BoardInfo,
    DiagComponent,
    DiagStatus,
    LanInfo,
    NetworkType,
    Node,
    NodeGeneralInfo,
    NodeSensorInfo,
    NodeType,
    NodeVentilationInfo,
    VentilationMode,
    VentilationState,
)


class DucoClient:
    """Client for a Duco box that exposes the local HTTP API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        *,
        port: int | None = None,
        request_timeout: float = 10.0,
    ) -> None:
        self._session = session
        self._timeout = aiohttp.ClientTimeout(total=request_timeout)

        parsed_host = urlsplit(host.rstrip("/") if "://" in host else f"//{host.rstrip('/')}")
        scheme = parsed_host.scheme.lower()

        if scheme == "https":
            msg = "HTTPS is not supported by this client"
            raise ValueError(msg)

        if scheme not in ("", "http"):
            msg = f"Unsupported scheme in host value: {host}"
            raise ValueError(msg)

        if parsed_host.username is not None or parsed_host.password is not None:
            msg = f"Host value must not include user credentials: {host}"
            raise ValueError(msg)

        if parsed_host.path not in ("", "/") or parsed_host.query or parsed_host.fragment:
            msg = f"Host value must not include a path, query, or fragment: {host}"
            raise ValueError(msg)

        normalized_host = parsed_host.hostname
        if normalized_host is None:
            msg = f"Invalid host value: {host}"
            raise ValueError(msg)

        try:
            embedded_port = parsed_host.port
        except ValueError as err:
            msg = f"Invalid port in host value: {host}"
            raise ValueError(msg) from err

        if embedded_port is not None and port is not None:
            msg = "Port specified both in host and port argument"
            raise ValueError(msg)

        if ":" in normalized_host:
            normalized_host = f"[{normalized_host}]"

        resolved_port = port if port is not None else embedded_port
        if resolved_port is None:
            self._base_url = f"http://{normalized_host}"
        else:
            self._base_url = f"http://{normalized_host}:{resolved_port}"

    @property
    def base_url(self) -> str:
        """Normalized base URL used for requests."""
        return self._base_url

    async def _request_json(self, method: str, path: str, **kwargs: Any) -> Any:
        if "json" in kwargs:
            payload = kwargs.pop("json")
            kwargs["data"] = json.dumps(payload, separators=(",", ":")).encode()
            kwargs.setdefault("headers", {})["Content-Type"] = "application/json"
        kwargs.setdefault("timeout", self._timeout)

        try:
            request = self._session.request(method, f"{self._base_url}{path}", **kwargs)
        except (aiohttp.ClientError, TimeoutError) as err:
            msg = f"Could not reach Duco device at {self._base_url}: {err}"
            raise DucoConnectionError(msg) from err

        try:
            async with request as response:
                if response.status == 429:
                    raise DucoWriteLimitError()

                if response.status >= 400:
                    body = await response.text()
                    msg = f"Unexpected response {response.status} for {path}: {body}"
                    raise DucoError(msg)

                try:
                    return await response.json(content_type=None)
                except ValueError as err:
                    msg = f"Expected JSON response from {path}: {err}"
                    raise DucoError(msg) from err
        except DucoError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            msg = f"Could not reach Duco device at {self._base_url}: {err}"
            raise DucoConnectionError(msg) from err

    @staticmethod
    def _read_wrapped_value(payload: dict[str, Any], key: str) -> Any:
        return payload[key]["Val"]

    @staticmethod
    def _to_node_type(raw_value: str) -> NodeType:
        try:
            return NodeType(raw_value)
        except ValueError:
            return NodeType.UNKNOWN

    @staticmethod
    def _to_network_type(raw_value: str) -> NetworkType:
        try:
            return NetworkType(raw_value)
        except ValueError:
            return NetworkType.UNKNOWN

    @staticmethod
    def _to_diag_status(raw_value: str) -> DiagStatus:
        try:
            return DiagStatus(raw_value)
        except ValueError:
            return DiagStatus.UNKNOWN

    async def async_get_api_info(self) -> ApiInfo:
        """Return API metadata advertised by the box."""
        payload = await self._request_json("GET", "/api")
        public_api_version = self._read_wrapped_value(payload, "PublicApiVersion")
        reported_api_version = None
        if "ApiVersion" in payload:
            reported_api_version = self._read_wrapped_value(payload, "ApiVersion")
        endpoints = [
            ApiEndpoint(
                url=item["Url"],
                methods=list(item.get("Methods", [])),
                query_parameters=list(item.get("QueryParameters", [])),
                modules=list(item.get("Modules", [])),
            )
            for item in payload.get("ApiInfo", [])
        ]
        return ApiInfo(
            public_api_version=public_api_version,
            reported_api_version=reported_api_version,
            endpoints=endpoints,
        )

    async def async_get_board_info(self) -> BoardInfo:
        """Return identity and version details for the main unit."""
        payload = await self._request_json(
            "GET",
            "/info",
            params={"module": "General", "submodule": "Board"},
        )
        board = payload["General"]["Board"]
        return BoardInfo(
            box_name=self._read_wrapped_value(board, "BoxName"),
            box_sub_type_name=self._read_wrapped_value(board, "BoxSubTypeName"),
            serial_board_box=self._read_wrapped_value(board, "SerialBoardBox"),
            serial_board_comm=self._read_wrapped_value(board, "SerialBoardComm"),
            serial_duco_box=self._read_wrapped_value(board, "SerialDucoBox"),
            serial_duco_comm=self._read_wrapped_value(board, "SerialDucoComm"),
            time=self._read_wrapped_value(board, "Time"),
            public_api_version=self._read_wrapped_value(board, "PublicApiVersion")
            if "PublicApiVersion" in board
            else None,
            software_version=self._read_wrapped_value(board, "SwVersion")
            if "SwVersion" in board
            else None,
        )

    async def async_get_lan_info(self) -> LanInfo:
        """Return LAN settings reported by the box."""
        payload = await self._request_json(
            "GET",
            "/info",
            params={"module": "General", "submodule": "Lan"},
        )
        lan = payload["General"]["Lan"]
        return LanInfo(
            mode=self._read_wrapped_value(lan, "Mode"),
            ip=self._read_wrapped_value(lan, "Ip"),
            net_mask=self._read_wrapped_value(lan, "NetMask"),
            default_gateway=self._read_wrapped_value(lan, "DefaultGateway"),
            dns=self._read_wrapped_value(lan, "Dns"),
            mac=self._read_wrapped_value(lan, "Mac"),
            host_name=self._read_wrapped_value(lan, "HostName"),
            rssi_wifi=self._read_wrapped_value(lan, "RssiWifi") if "RssiWifi" in lan else None,
        )

    async def async_get_diagnostics(self) -> list[DiagComponent]:
        """Return health states for diagnostic subsystems."""
        payload = await self._request_json("GET", "/info", params={"module": "Diag"})
        return [
            DiagComponent(
                component=item["Component"],
                status=self._to_diag_status(item["Status"]),
            )
            for item in payload["Diag"]["SubSystems"]
        ]

    async def async_get_nodes(self) -> list[Node]:
        """Return nodes reported by the local API."""
        payload = await self._request_json("GET", "/info/nodes")
        return [self._parse_node(item) for item in payload["Nodes"]]

    async def async_get_write_requests_remaining(self) -> int:
        """Return the remaining write budget reported by the box."""
        payload = await self._request_json(
            "GET",
            "/info",
            params={"module": "General", "submodule": "PublicApi"},
        )
        return int(self._read_wrapped_value(payload["General"]["PublicApi"], "WriteReqCntRemain"))

    async def async_set_ventilation_state(
        self, node_id: int, state: VentilationState | str
    ) -> None:
        """Request a ventilation state change for a node."""
        state_value = state.value if isinstance(state, VentilationState) else state
        await self._request_json(
            "POST",
            f"/action/nodes/{node_id}",
            json={"Action": "SetVentilationState", "Val": state_value},
        )

    def _parse_node(self, payload: dict[str, Any]) -> Node:
        general = payload["General"]
        node_general = NodeGeneralInfo(
            node_type=self._to_node_type(self._read_wrapped_value(general, "Type")),
            sub_type=self._read_wrapped_value(general, "SubType"),
            network_type=self._to_network_type(self._read_wrapped_value(general, "NetworkType")),
            parent=self._read_wrapped_value(general, "Parent"),
            asso=self._read_wrapped_value(general, "Asso"),
            name=self._read_wrapped_value(general, "Name"),
            identify=self._read_wrapped_value(general, "Identify"),
        )

        ventilation = None
        if "Ventilation" in payload:
            vent = payload["Ventilation"]
            ventilation = NodeVentilationInfo(
                state=VentilationState(self._read_wrapped_value(vent, "State")),
                mode=VentilationMode(self._read_wrapped_value(vent, "Mode")),
                time_state_remain=self._read_wrapped_value(vent, "TimeStateRemain"),
                time_state_end=self._read_wrapped_value(vent, "TimeStateEnd"),
                flow_lvl_tgt=self._read_wrapped_value(vent, "FlowLvlTgt")
                if "FlowLvlTgt" in vent
                else None,
            )

        sensor = None
        if "Sensor" in payload:
            sensor = payload["Sensor"]
            sensor = NodeSensorInfo(
                co2=self._read_wrapped_value(sensor, "Co2") if "Co2" in sensor else None,
                iaq_co2=self._read_wrapped_value(sensor, "IaqCo2") if "IaqCo2" in sensor else None,
                rh=self._read_wrapped_value(sensor, "Rh") if "Rh" in sensor else None,
                iaq_rh=self._read_wrapped_value(sensor, "IaqRh") if "IaqRh" in sensor else None,
                temp=self._read_wrapped_value(sensor, "Temp") if "Temp" in sensor else None,
            )

        return Node(
            node_id=payload["Node"],
            general=node_general,
            ventilation=ventilation,
            sensor=sensor,
        )
