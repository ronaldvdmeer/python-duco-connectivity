"""Async client for the local Duco HTTP API."""

import json
import logging
import sys
from types import FrameType
from typing import Any, Literal
from urllib.parse import urlsplit

import aiohttp

from .exceptions import DucoConnectionError, DucoError, DucoWriteLimitError
from .models import (
    ActionResult,
    ActionResultStatus,
    ApiEndpoint,
    ApiInfo,
    BoardInfo,
    Config,
    ConfigItem,
    ConfigNode,
    ConfigNodeOverview,
    ConfigNodeStruct,
    ConfigSection,
    ConfigValue,
    ConfigValueOptions,
    ConfigValueString,
    DiagComponent,
    DiagStatus,
    LanInfo,
    NetworkType,
    Node,
    NodeGeneralInfo,
    NodeOverview,
    NodeSensorInfo,
    NodeType,
    NodeVentilationInfo,
    PatchConfigValue,
    VentilationMode,
    VentilationState,
)

_LOGGER = logging.getLogger(__name__)


def _compat_caller() -> str | None:
    """Return the first external caller that reached a compatibility path."""
    frame: FrameType | None = sys._getframe(1)

    while frame is not None:
        module_name = frame.f_globals.get("__name__", "")
        if module_name != "duco_connectivity" and not module_name.startswith("duco_connectivity."):
            return f"{module_name}.{frame.f_code.co_name}"
        frame = frame.f_back

    return None


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

        raw_host = host.rstrip("/")
        authority = raw_host.split("://", 1)[1] if "://" in raw_host else raw_host
        authority = authority.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]

        if "@" not in authority and authority.count(":") >= 2 and not authority.startswith("["):
            msg = "Unbracketed IPv6 host values are not supported; use [addr] or [addr]:port"
            raise ValueError(msg)

        parsed_host = urlsplit(raw_host if "://" in host else f"//{raw_host}")
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

        if port is not None and not 0 <= port <= 65535:
            msg = f"Invalid port argument: {port}"
            raise ValueError(msg)

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

        _LOGGER.debug("Initialized DucoClient for %s", self._base_url)
        _LOGGER.debug(
            "Using HTTP-only duco_connectivity transport for %s.",
            self._base_url,
        )

    @property
    def base_url(self) -> str:
        """Normalized base URL used for requests."""
        return self._base_url

    async def _request_json(self, method: str, path: str, **kwargs: Any) -> Any:
        json_payload = None
        if "json" in kwargs:
            json_payload = kwargs.pop("json")
            kwargs["data"] = json.dumps(json_payload, separators=(",", ":")).encode()
            kwargs.setdefault("headers", {})["Content-Type"] = "application/json"
        kwargs.setdefault("timeout", self._timeout)

        _LOGGER.debug(
            "Requesting %s %s%s with params=%s json=%s",
            method,
            self._base_url,
            path,
            kwargs.get("params"),
            json_payload,
        )

        try:
            request = self._session.request(method, f"{self._base_url}{path}", **kwargs)
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.debug(
                "Request setup failed for %s %s%s: %s",
                method,
                self._base_url,
                path,
                err,
            )
            msg = f"Could not reach Duco device at {self._base_url}: {err}"
            raise DucoConnectionError(msg) from err

        try:
            async with request as response:
                _LOGGER.debug(
                    "Received response %s for %s %s%s",
                    response.status,
                    method,
                    self._base_url,
                    path,
                )
                if response.status == 429:
                    _LOGGER.debug(
                        "Write limit reached for %s %s%s",
                        method,
                        self._base_url,
                        path,
                    )
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
            _LOGGER.debug(
                "Request failed for %s %s%s: %s",
                method,
                self._base_url,
                path,
                err,
            )
            msg = f"Could not reach Duco device at {self._base_url}: {err}"
            raise DucoConnectionError(msg) from err

    @staticmethod
    def _read_wrapped_value(payload: dict[str, Any], key: str) -> Any:
        return payload[key]["Val"]

    @staticmethod
    def _read_scalar_value(payload: dict[str, Any], key: str) -> Any:
        raw_value = payload[key]
        if not isinstance(raw_value, dict):
            return raw_value

        if "Val" not in raw_value:
            msg = f"Expected direct value or wrapped Val object for {key}"
            raise DucoError(msg)

        return raw_value["Val"]

    @classmethod
    def _parse_config(cls, payload: Any) -> Config:
        if not isinstance(payload, dict):
            msg = f"Expected object payload from /config, got {type(payload).__name__}"
            raise DucoError(msg)

        return Config(
            sections={
                key: cls._parse_config_section(value, path=key) for key, value in payload.items()
            }
        )

    @classmethod
    def _parse_config_section(cls, payload: Any, *, path: str) -> ConfigSection:
        if not isinstance(payload, dict):
            msg = f"Expected object for config section {path}, got {type(payload).__name__}"
            raise DucoError(msg)

        return ConfigSection(
            entries={
                key: cls._parse_config_item(value, path=f"{path}.{key}")
                for key, value in payload.items()
            }
        )

    @classmethod
    def _parse_config_item(
        cls,
        payload: Any,
        *,
        path: str,
    ) -> ConfigItem:
        if not isinstance(payload, dict):
            msg = f"Expected object for config entry {path}, got {type(payload).__name__}"
            raise DucoError(msg)

        if "Val" not in payload:
            return cls._parse_config_section(payload, path=path)

        raw_value = payload["Val"]
        if isinstance(raw_value, str):
            return ConfigValueString(value=raw_value)

        if type(raw_value) is not int:
            msg = f"Unsupported config value type {type(raw_value).__name__} for {path}"
            raise DucoError(msg)

        for key in ("Min", "Inc", "Max"):
            if key in payload and type(payload[key]) is not int:
                msg = f"Expected integer {key} for config entry {path}"
                raise DucoError(msg)

        options = payload.get("Options")
        if options is not None and (
            not isinstance(options, list) or any(type(item) is not int for item in options)
        ):
            msg = f"Expected integer option list for config entry {path}"
            raise DucoError(msg)

        has_range_metadata = any(key in payload for key in ("Min", "Inc", "Max"))
        if options is not None and has_range_metadata:
            msg = f"Config entry {path} cannot combine range metadata with Options"
            raise DucoError(msg)

        if options is not None:
            return ConfigValueOptions(
                value=raw_value,
                options=tuple(options),
            )

        return ConfigValue(
            value=raw_value,
            minimum=payload.get("Min"),
            increment=payload.get("Inc"),
            maximum=payload.get("Max"),
        )

    @staticmethod
    def _normalize_patch_config_scalar(raw_value: Any, *, path: str) -> int | str:
        if isinstance(raw_value, str):
            return raw_value

        if type(raw_value) is int:
            return raw_value

        msg = f"Unsupported patch config value type {type(raw_value).__name__} for {path}"
        raise ValueError(msg)

    @classmethod
    def _normalize_patch_config_payload(cls, payload: Any, *, path: str) -> dict[str, Any]:
        if not isinstance(payload, dict):
            msg = f"Expected object payload for {path}, got {type(payload).__name__}"
            raise ValueError(msg)

        normalized: dict[str, Any] = {}
        for key, value in payload.items():
            if not isinstance(key, str):
                msg = f"Expected string key for {path}, got {type(key).__name__}"
                raise ValueError(msg)

            item_path = f"{path}.{key}"
            if isinstance(value, PatchConfigValue):
                normalized[key] = {
                    "Val": cls._normalize_patch_config_scalar(value.value, path=item_path)
                }
                continue

            if not isinstance(value, dict):
                msg = (
                    f"Unsupported patch config payload type {type(value).__name__} for {item_path}"
                )
                raise ValueError(msg)

            if "Val" in value:
                if tuple(value) != ("Val",):
                    msg = f"Patch config leaf {item_path} may only contain Val"
                    raise ValueError(msg)

                normalized[key] = {
                    "Val": cls._normalize_patch_config_scalar(value["Val"], path=item_path)
                }
                continue

            normalized[key] = cls._normalize_patch_config_payload(value, path=item_path)

        return normalized

    @classmethod
    def _parse_config_node_string_value(
        cls,
        payload: Any,
        *,
        path: str,
    ) -> ConfigValueString:
        if not isinstance(payload, dict):
            msg = f"Expected object for node config value {path}, got {type(payload).__name__}"
            raise DucoError(msg)

        if "Val" not in payload:
            msg = f"Expected Val in node config value {path}"
            raise DucoError(msg)

        raw_value = payload["Val"]
        if not isinstance(raw_value, str):
            msg = (
                f"Expected string Val for node config value {path}, got {type(raw_value).__name__}"
            )
            raise DucoError(msg)

        return ConfigValueString(value=raw_value)

    @classmethod
    def _parse_config_node_struct(
        cls,
        payload: Any,
        *,
        path: str,
    ) -> ConfigNodeStruct:
        if not isinstance(payload, dict):
            msg = f"Expected object for node config struct {path}, got {type(payload).__name__}"
            raise DucoError(msg)

        name = None
        if "Name" in payload:
            name = cls._parse_config_node_string_value(payload["Name"], path=f"{path}.Name")

        return ConfigNodeStruct(name=name)

    @classmethod
    def _parse_config_node_overview(cls, payload: Any) -> ConfigNodeOverview:
        if not isinstance(payload, dict):
            msg = f"Expected object payload from /config/nodes, got {type(payload).__name__}"
            raise DucoError(msg)

        if "Nodes" not in payload or not isinstance(payload["Nodes"], list):
            msg = "Expected list Nodes in /config/nodes response"
            raise DucoError(msg)

        nodes: list[ConfigNode] = []
        for index, item in enumerate(payload["Nodes"]):
            if not isinstance(item, dict):
                msg = (
                    f"Expected object item at index {index} in /config/nodes response, "
                    f"got {type(item).__name__}"
                )
                raise DucoError(msg)

            if "Node" not in item:
                msg = f"Expected integer Node in /config/nodes item at index {index}"
                raise DucoError(msg)

            node_id = cls._read_scalar_value(item, "Node")
            if type(node_id) is not int:
                msg = (
                    f"Expected integer Node in /config/nodes item at index {index}, "
                    f"got {type(node_id).__name__}"
                )
                raise DucoError(msg)

            node_struct = cls._parse_config_node_struct(
                item,
                path=f"/config/nodes item at index {index}",
            )
            nodes.append(ConfigNode(node_id=node_id, name=node_struct.name))

        return ConfigNodeOverview(nodes=nodes)

    @classmethod
    def _parse_config_node(cls, payload: Any, *, path: str) -> ConfigNode:
        if not isinstance(payload, dict):
            msg = f"Expected object payload from {path}, got {type(payload).__name__}"
            raise DucoError(msg)

        if "Node" not in payload:
            msg = f"Expected integer Node in {path} response"
            raise DucoError(msg)

        node_id = cls._read_scalar_value(payload, "Node")
        if type(node_id) is not int:
            msg = f"Expected integer Node in {path} response, got {type(node_id).__name__}"
            raise DucoError(msg)

        node_struct = cls._parse_config_node_struct(payload, path=path)
        return ConfigNode(node_id=node_id, name=node_struct.name)

    @staticmethod
    def _to_node_type(raw_value: str) -> NodeType:
        try:
            return NodeType(raw_value)
        except ValueError:
            _LOGGER.debug(
                "Unknown node type %r received from Duco API; falling back to UNKNOWN",
                raw_value,
            )
            return NodeType.UNKNOWN

    @staticmethod
    def _to_network_type(raw_value: str) -> NetworkType:
        try:
            return NetworkType(raw_value)
        except ValueError:
            _LOGGER.debug(
                "Unknown network type %r received from Duco API; falling back to UNKNOWN",
                raw_value,
            )
            return NetworkType.UNKNOWN

    @staticmethod
    def _to_diag_status(raw_value: str) -> DiagStatus:
        try:
            return DiagStatus(raw_value)
        except ValueError:
            _LOGGER.debug(
                "Unknown diagnostic status %r received from Duco API; falling back to UNKNOWN",
                raw_value,
            )
            return DiagStatus.UNKNOWN

    @staticmethod
    def _to_action_result_status(raw_value: str) -> ActionResultStatus:
        try:
            return ActionResultStatus(raw_value)
        except ValueError:
            _LOGGER.debug(
                "Unknown action result status %r received from Duco API; falling back to UNKNOWN",
                raw_value,
            )
            return ActionResultStatus.UNKNOWN

    @staticmethod
    def _to_ventilation_state(raw_value: str) -> VentilationState:
        try:
            return VentilationState(raw_value)
        except ValueError:
            _LOGGER.debug(
                "Unknown ventilation state %r received from Duco API; falling back to UNKNOWN",
                raw_value,
            )
            return VentilationState.UNKNOWN

    @staticmethod
    def _to_ventilation_mode(raw_value: str) -> VentilationMode:
        try:
            return VentilationMode(raw_value)
        except ValueError:
            _LOGGER.debug(
                "Unknown ventilation mode %r received from Duco API; falling back to UNKNOWN",
                raw_value,
            )
            return VentilationMode.UNKNOWN

    @classmethod
    def _parse_action_result(cls, payload: Any) -> ActionResult:
        if not isinstance(payload, dict):
            msg = f"Expected object payload from node action, got {type(payload).__name__}"
            raise DucoError(msg)

        if "Result" not in payload:
            msg = "Expected Result in node action response"
            raise DucoError(msg)

        result = cls._read_scalar_value(payload, "Result")
        if not isinstance(result, str):
            msg = f"Expected string Result in node action response, got {type(result).__name__}"
            raise DucoError(msg)

        code: int | None = None
        if "Code" in payload:
            code = cls._read_scalar_value(payload, "Code")
            if type(code) is not int:
                msg = f"Expected integer Code in node action response, got {type(code).__name__}"
                raise DucoError(msg)

        message: str | None = None
        if "Message" in payload:
            message = cls._read_scalar_value(payload, "Message")
            if not isinstance(message, str):
                msg = (
                    f"Expected string Message in node action response, got {type(message).__name__}"
                )
                raise DucoError(msg)

        return ActionResult(
            result=cls._to_action_result_status(result),
            code=code,
            message=message,
        )

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

    async def async_get_info(
        self,
        module: str | None = None,
        submodule: str | None = None,
        parameter: str | None = None,
    ) -> Any:
        """Return the raw payload from the generic info endpoint."""
        params: dict[str, str] = {}
        if module is not None:
            params["module"] = module
        if submodule is not None:
            params["submodule"] = submodule
        if parameter is not None:
            params["parameter"] = parameter

        if params:
            return await self._request_json("GET", "/info", params=params)

        return await self._request_json("GET", "/info")

    async def async_get_config(
        self,
        module: str | None = None,
        submodule: str | None = None,
        parameter: str | None = None,
    ) -> Config:
        """Return configuration values from the generic config endpoint."""
        params: dict[str, str] = {}
        if module is not None:
            params["module"] = module
        if submodule is not None:
            params["submodule"] = submodule
        if parameter is not None:
            params["parameter"] = parameter

        if params:
            payload = await self._request_json("GET", "/config", params=params)
        else:
            payload = await self._request_json("GET", "/config")

        return self._parse_config(payload)

    async def async_set_config(
        self,
        payload: dict[str, Any],
        module: str | None = None,
        submodule: str | None = None,
        parameter: str | None = None,
    ) -> Config:
        """Patch configuration values through the generic config endpoint."""
        params: dict[str, str] = {}
        if module is not None:
            params["module"] = module
        if submodule is not None:
            params["submodule"] = submodule
        if parameter is not None:
            params["parameter"] = parameter

        normalized_payload = self._normalize_patch_config_payload(payload, path="config")

        if params:
            response = await self._request_json(
                "PATCH",
                "/config",
                params=params,
                json=normalized_payload,
            )
        else:
            response = await self._request_json(
                "PATCH",
                "/config",
                json=normalized_payload,
            )

        return self._parse_config(response)

    async def async_get_node_configs(
        self,
        parameter: Literal["Name"] | None = None,
    ) -> ConfigNodeOverview:
        """Return node-level configuration values from `/config/nodes`.

        When provided, `parameter` currently supports only `Name`, which is the
        node-level field exposed by the typed config node models.
        """
        params: dict[str, str] = {}
        if parameter is not None:
            if parameter != "Name":
                msg = "async_get_node_configs only supports parameter='Name'"
                raise ValueError(msg)
            params["parameter"] = parameter

        if params:
            payload = await self._request_json("GET", "/config/nodes", params=params)
        else:
            payload = await self._request_json("GET", "/config/nodes")

        return self._parse_config_node_overview(payload)

    async def async_get_node_config(
        self,
        node_id: int,
        parameter: Literal["Name"] | None = None,
    ) -> ConfigNode:
        """Return node-level configuration values from `/config/nodes/{node}`.

        When provided, `parameter` currently supports only `Name`, which is the
        node-level field exposed by the typed config node models.
        """
        params: dict[str, str] = {}
        if parameter is not None:
            if parameter != "Name":
                msg = "async_get_node_config only supports parameter='Name'"
                raise ValueError(msg)
            params["parameter"] = parameter

        path = f"/config/nodes/{node_id}"
        if params:
            payload = await self._request_json("GET", path, params=params)
        else:
            payload = await self._request_json("GET", path)

        return self._parse_config_node(payload, path=path)

    async def async_get_board_info(self) -> BoardInfo:
        """Return identity and version details for the main unit."""
        payload = await self.async_get_info(
            module="General",
            submodule="Board",
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
        payload = await self.async_get_info(
            module="General",
            submodule="Lan",
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
        payload = await self.async_get_info(module="Diag")
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

    async def async_get_nodes_overview(self) -> list[NodeOverview]:
        """Return lightweight node identifiers reported by the local API."""
        payload = await self._request_json("GET", "/nodes")
        return self._parse_nodes_overview(payload)

    async def async_get_node_info(
        self,
        node_id: int,
        module: str | None = None,
        parameter: str | None = None,
    ) -> Node:
        """Return detailed information for a specific node."""
        params: dict[str, str] = {}
        if module is not None:
            params["module"] = module
        if parameter is not None:
            params["parameter"] = parameter

        if params:
            payload = await self._request_json(
                "GET",
                f"/info/nodes/{node_id}",
                params=params,
            )
        else:
            payload = await self._request_json("GET", f"/info/nodes/{node_id}")

        return self._parse_node(payload)

    async def async_get_write_requests_remaining(self) -> int:
        """Return the remaining write budget reported by the box."""
        payload = await self.async_get_info(
            module="General",
            submodule="PublicApi",
        )
        return int(self._read_wrapped_value(payload["General"]["PublicApi"], "WriteReqCntRemain"))

    async def async_get_write_req_remaining(self) -> int:
        """Backward-compatible alias for the old write budget method name."""
        caller = _compat_caller()
        if caller is None:
            _LOGGER.debug(
                "Compatibility alias async_get_write_req_remaining() used; "
                "delegating to async_get_write_requests_remaining()."
            )
        else:
            _LOGGER.debug(
                "Compatibility alias async_get_write_req_remaining() used by %s; "
                "delegating to async_get_write_requests_remaining().",
                caller,
            )
        return await self.async_get_write_requests_remaining()

    async def async_set_ventilation_state(
        self, node_id: int, state: VentilationState | str
    ) -> None:
        """Request a ventilation state change for a node."""
        state_value = state.value if isinstance(state, VentilationState) else state
        await self.async_set_node_action(
            node_id=node_id,
            action="SetVentilationState",
            val=state_value,
        )

    async def async_set_node_action(
        self,
        node_id: int,
        action: str,
        val: str | int | bool | None = None,
    ) -> ActionResult:
        """Execute a generic node action through the local Duco API."""
        payload: dict[str, str | int | bool] = {"Action": action}
        if val is not None:
            payload["Val"] = val

        response = await self._request_json(
            "POST",
            f"/action/nodes/{node_id}",
            json=payload,
        )
        return self._parse_action_result(response)

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
                state=self._to_ventilation_state(self._read_wrapped_value(vent, "State")),
                mode=self._to_ventilation_mode(self._read_wrapped_value(vent, "Mode")),
                time_state_remain=self._read_wrapped_value(vent, "TimeStateRemain"),
                time_state_end=self._read_wrapped_value(vent, "TimeStateEnd"),
                flow_lvl_tgt=self._read_wrapped_value(vent, "FlowLvlTgt")
                if "FlowLvlTgt" in vent
                else None,
            )

        sensor = None
        if "Sensor" in payload:
            sensor_payload = payload["Sensor"]
            sensor = NodeSensorInfo(
                co2=self._read_wrapped_value(sensor_payload, "Co2")
                if "Co2" in sensor_payload
                else None,
                iaq_co2=self._read_wrapped_value(sensor_payload, "IaqCo2")
                if "IaqCo2" in sensor_payload
                else None,
                rh=self._read_wrapped_value(sensor_payload, "Rh")
                if "Rh" in sensor_payload
                else None,
                iaq_rh=self._read_wrapped_value(sensor_payload, "IaqRh")
                if "IaqRh" in sensor_payload
                else None,
                temp=self._read_wrapped_value(sensor_payload, "Temp")
                if "Temp" in sensor_payload
                else None,
            )

        return Node(
            node_id=payload["Node"],
            general=node_general,
            ventilation=ventilation,
            sensor=sensor,
        )

    @classmethod
    def _parse_nodes_overview(cls, payload: Any) -> list[NodeOverview]:
        if not isinstance(payload, list):
            msg = f"Expected list payload from /nodes, got {type(payload).__name__}"
            raise DucoError(msg)

        nodes: list[NodeOverview] = []
        for index, item in enumerate(payload):
            if not isinstance(item, dict):
                msg = (
                    f"Expected object item at index {index} from /nodes, got {type(item).__name__}"
                )
                raise DucoError(msg)

            if "Node" not in item:
                msg = f"Expected integer Node in /nodes item at index {index}"
                raise DucoError(msg)

            node_id = cls._read_scalar_value(item, "Node")
            if type(node_id) is not int:
                msg = (
                    f"Expected integer Node in /nodes item at index {index}, "
                    f"got {type(node_id).__name__}"
                )
                raise DucoError(msg)

            nodes.append(NodeOverview(node_id=node_id))

        return nodes
