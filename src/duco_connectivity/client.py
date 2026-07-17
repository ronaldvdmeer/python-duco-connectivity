"""Async client for the local Duco HTTP API."""

import json
import logging
import math
import sys
from dataclasses import fields, is_dataclass
from decimal import Decimal, InvalidOperation
from types import FrameType
from typing import Any, Literal, cast
from urllib.parse import urlsplit

import aiohttp

from .exceptions import (
    DucoConnectionError,
    DucoError,
    DucoResponseError,
    DucoUnsupportedCapabilityError,
    DucoWriteLimitError,
)
from .models import (
    ActionItem,
    ActionItemList,
    ActionName,
    ActionResult,
    ActionResultStatus,
    ActionValueType,
    ApiEndpoint,
    ApiInfo,
    BoardInfo,
    BypassSupplyTemperatureTarget,
    Config,
    ConfigAutoRebootComm,
    ConfigGeneral,
    ConfigGeneralSubmoduleSelector,
    ConfigGroup,
    ConfigGroupStruct,
    ConfigHeatRecovery,
    ConfigHeatRecoveryBypass,
    ConfigHeatRecoverySubmoduleSelector,
    ConfigItem,
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
    ConfigZoneStruct,
    ConfigZoneWithGroupStruct,
    DeviceGroupConfigSubmoduleSelector,
    DiagComponent,
    DiagInfo,
    InfoGeneralSubmoduleSelector,
    InfoGroup,
    InfoGroupStruct,
    InfoModuleSelector,
    InfoZone,
    InfoZoneGroup,
    InfoZonesOverview,
    InfoZoneStruct,
    LanInfo,
    NetworkType,
    Node,
    NodeActionItemList,
    NodeGeneralInfo,
    NodeInfoModuleSelector,
    NodeListActionItemList,
    NodeMotorStateInfo,
    NodeOverview,
    NodeSensorInfo,
    NodeType,
    NodeVentilationInfo,
    PatchConfigModel,
    PatchConfigNodeStruct,
    PatchConfigNodeValue,
    PatchConfigValue,
    PatchConfigZoneStruct,
    VentilationMode,
    VentilationState,
    VentilationTemperatureInfo,
    ZoneModuleSelector,
    _PatchPayloadModel,
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


def _is_unsupported_optional_endpoint_error(error: DucoResponseError, path: str) -> bool:
    """Return whether a Duco response reports an unavailable optional endpoint."""
    if error.status != 400 or error.path != path:
        return False

    try:
        error_payload = cast(object, json.loads(error.body))
    except json.JSONDecodeError:
        return False

    if not isinstance(error_payload, dict):
        return False

    response = cast(dict[str, object], error_payload)
    return response.get("Code") == 3 and response.get("Result") == "FAILED"


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

    @staticmethod
    def _normalize_raw_get_path(path: str) -> str:
        """Validate and normalize a public raw-read path."""
        parsed_path = urlsplit(path)
        if parsed_path.scheme or parsed_path.netloc:
            msg = "async_get_raw path must be API-relative, not a full URL"
            raise ValueError(msg)

        if not path.startswith("/"):
            msg = "async_get_raw path must start with /"
            raise ValueError(msg)

        if parsed_path.query or parsed_path.fragment:
            msg = (
                "async_get_raw path must not include a query string or fragment; use params instead"
            )
            raise ValueError(msg)

        return parsed_path.path

    async def _request_json(self, method: str, path: str, **kwargs: Any) -> Any:
        allow_empty_response = kwargs.pop("allow_empty_response", False)
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
                    body = await response.text()
                    _LOGGER.debug(
                        "Write limit reached for %s %s%s",
                        method,
                        self._base_url,
                        path,
                    )
                    raise DucoWriteLimitError(path=path, body=body)

                if response.status >= 400:
                    body = await response.text()
                    raise DucoResponseError(response.status, path, body)

                try:
                    return await response.json(content_type=None)
                except ValueError as err:
                    if allow_empty_response:
                        body = await response.text()
                        if not body.strip():
                            return None
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
    def _read_optional_wrapped_int(
        payload: dict[str, Any],
        key: str,
        *,
        path: str,
    ) -> int | None:
        """Read an optional wrapped integer from a typed-stable API branch."""
        if key not in payload:
            return None
        raw_entry = payload[key]
        if not isinstance(raw_entry, dict):
            msg = f"Expected wrapped Val object for {path}.{key}, got {type(raw_entry).__name__}"
            raise DucoError(msg)
        if "Val" not in raw_entry:
            msg = f"Expected wrapped Val object for {path}.{key}"
            raise DucoError(msg)

        raw_value = raw_entry["Val"]
        if type(raw_value) is not int:
            msg = f"Expected integer value for {path}.{key}, got {type(raw_value).__name__}"
            raise DucoError(msg)

        return raw_value

    @staticmethod
    def _validate_bypass_zone_id(zone_id: int) -> str:
        """Return the API parameter name for a supported bypass target zone."""
        if type(zone_id) is not int or not 1 <= zone_id <= 8:
            msg = "zone_id must be an integer between 1 and 8"
            raise ValueError(msg)
        return f"TempSupTgtZone{zone_id}"

    @staticmethod
    def _decicelsius_to_celsius(value: int) -> float:
        """Convert Duco decicelsius values to Celsius floats."""
        return value / 10.0

    @classmethod
    def _celsius_to_decicelsius(cls, value: float, *, path: str) -> int:
        """Convert a Celsius float to the Duco decicelsius integer representation."""
        if type(value) not in (int, float):
            msg = f"{path} must be an int or float, got {type(value).__name__}"
            raise ValueError(msg)

        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            msg = f"{path} must be a finite temperature value"
            raise ValueError(msg)

        try:
            scaled = Decimal(str(value)) * 10
        except InvalidOperation as err:
            msg = f"{path} must be representable as a decimal temperature"
            raise ValueError(msg) from err

        if scaled != scaled.to_integral_value():
            msg = f"{path} must be representable in 0.1°C increments"
            raise ValueError(msg)

        return int(scaled)

    @classmethod
    def _build_bypass_supply_temperature_target(
        cls,
        zone_id: int,
        value: ConfigValue,
    ) -> BypassSupplyTemperatureTarget:
        """Convert a raw config value into a Celsius convenience model."""
        return BypassSupplyTemperatureTarget(
            zone_id=zone_id,
            value=cls._decicelsius_to_celsius(value.value),
            minimum=None if value.minimum is None else cls._decicelsius_to_celsius(value.minimum),
            increment=None
            if value.increment is None
            else cls._decicelsius_to_celsius(value.increment),
            maximum=None if value.maximum is None else cls._decicelsius_to_celsius(value.maximum),
            raw_payload=cls._preserve_raw_payload(value.raw_payload),
        )

    @classmethod
    def _extract_bypass_supply_temperature_target(
        cls,
        config: Config,
        zone_id: int,
    ) -> BypassSupplyTemperatureTarget | None:
        """Read a single bypass supply target from a typed config response."""
        heat_recovery = config.heat_recovery
        if heat_recovery is None or heat_recovery.bypass is None:
            return None

        raw_value = getattr(heat_recovery.bypass, f"temp_sup_tgt_zone_{zone_id}")
        if raw_value is None:
            return None

        return cls._build_bypass_supply_temperature_target(zone_id, raw_value)

    @staticmethod
    def _read_scalar_value(payload: dict[str, Any], key: str) -> Any:
        raw_value = payload[key]
        if not isinstance(raw_value, dict):
            return raw_value

        if "Val" not in raw_value:
            msg = f"Expected direct value or wrapped Val object for {key}"
            raise DucoError(msg)

        return raw_value["Val"]

    @staticmethod
    def _preserve_raw_payload(payload: dict[str, Any]) -> dict[str, Any]:
        return payload

    @classmethod
    def _parse_config(cls, payload: Any) -> Config:
        if not isinstance(payload, dict):
            msg = f"Expected object payload from /config, got {type(payload).__name__}"
            raise DucoError(msg)

        sections = {
            key: cls._parse_config_section(value, path=key) for key, value in payload.items()
        }

        return Config(
            sections=sections,
            general=cls._build_config_general(sections.get("General"), path="General"),
            heat_recovery=cls._build_config_heat_recovery(
                sections.get("HeatRecovery"),
                path="HeatRecovery",
            ),
            raw_payload=cls._preserve_raw_payload(payload),
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
            },
            raw_payload=cls._preserve_raw_payload(payload),
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
            return ConfigValueString(
                value=raw_value,
                raw_payload=cls._preserve_raw_payload(payload),
            )

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
                raw_payload=cls._preserve_raw_payload(payload),
            )

        return ConfigValue(
            value=raw_value,
            minimum=payload.get("Min"),
            increment=payload.get("Inc"),
            maximum=payload.get("Max"),
            raw_payload=cls._preserve_raw_payload(payload),
        )

    @staticmethod
    def _read_optional_config_section(
        section: ConfigSection,
        key: str,
        *,
        path: str,
    ) -> ConfigSection | None:
        value = section.entries.get(key)
        if value is None:
            return None
        if not isinstance(value, ConfigSection):
            msg = f"Expected config section {path}.{key}, got {type(value).__name__}"
            raise DucoError(msg)
        return value

    @staticmethod
    def _read_optional_config_value(
        section: ConfigSection,
        key: str,
        *,
        path: str,
    ) -> ConfigValue | None:
        value = section.entries.get(key)
        if value is None:
            return None
        if not isinstance(value, ConfigValue):
            msg = f"Expected integer config value {path}.{key}, got {type(value).__name__}"
            raise DucoError(msg)
        return value

    @staticmethod
    def _read_optional_config_string_value(
        section: ConfigSection,
        key: str,
        *,
        path: str,
    ) -> ConfigValueString | None:
        value = section.entries.get(key)
        if value is None:
            return None
        if not isinstance(value, ConfigValueString):
            msg = f"Expected string config value {path}.{key}, got {type(value).__name__}"
            raise DucoError(msg)
        return value

    @classmethod
    def _build_config_time(cls, section: ConfigSection | None, *, path: str) -> ConfigTime | None:
        if section is None:
            return None

        return ConfigTime(
            time_zone=cls._read_optional_config_value(section, "TimeZone", path=path),
            dst=cls._read_optional_config_value(section, "Dst", path=path),
            raw_payload=cls._preserve_raw_payload(section.raw_payload),
        )

    @classmethod
    def _build_config_modbus(
        cls,
        section: ConfigSection | None,
        *,
        path: str,
    ) -> ConfigModbus | None:
        if section is None:
            return None

        return ConfigModbus(
            addr=cls._read_optional_config_value(section, "Addr", path=path),
            offset=cls._read_optional_config_value(section, "Offset", path=path),
            raw_payload=cls._preserve_raw_payload(section.raw_payload),
        )

    @classmethod
    def _build_config_lan(cls, section: ConfigSection | None, *, path: str) -> ConfigLan | None:
        if section is None:
            return None

        return ConfigLan(
            mode=cls._read_optional_config_value(section, "Mode", path=path),
            dhcp=cls._read_optional_config_value(section, "Dhcp", path=path),
            static_ip=cls._read_optional_config_string_value(section, "StaticIp", path=path),
            static_net_mask=cls._read_optional_config_string_value(
                section,
                "StaticNetMask",
                path=path,
            ),
            static_default_gateway=cls._read_optional_config_string_value(
                section,
                "StaticDefaultGateway",
                path=path,
            ),
            static_dns=cls._read_optional_config_string_value(section, "StaticDns", path=path),
            wifi_client_ssid=cls._read_optional_config_string_value(
                section,
                "WifiClientSsid",
                path=path,
            ),
            wifi_client_key=cls._read_optional_config_string_value(
                section,
                "WifiClientKey",
                path=path,
            ),
            raw_payload=cls._preserve_raw_payload(section.raw_payload),
        )

    @classmethod
    def _build_config_auto_reboot_comm(
        cls,
        section: ConfigSection | None,
        *,
        path: str,
    ) -> ConfigAutoRebootComm | None:
        if section is None:
            return None

        return ConfigAutoRebootComm(
            period=cls._read_optional_config_value(section, "Period", path=path),
            time=cls._read_optional_config_value(section, "Time", path=path),
            raw_payload=cls._preserve_raw_payload(section.raw_payload),
        )

    @classmethod
    def _build_config_general(
        cls,
        section: ConfigSection | None,
        *,
        path: str,
    ) -> ConfigGeneral | None:
        if section is None:
            return None

        return ConfigGeneral(
            time=cls._build_config_time(
                cls._read_optional_config_section(section, "Time", path=path),
                path=f"{path}.Time",
            ),
            modbus=cls._build_config_modbus(
                cls._read_optional_config_section(section, "Modbus", path=path),
                path=f"{path}.Modbus",
            ),
            lan=cls._build_config_lan(
                cls._read_optional_config_section(section, "Lan", path=path),
                path=f"{path}.Lan",
            ),
            auto_reboot_comm=cls._build_config_auto_reboot_comm(
                cls._read_optional_config_section(section, "AutoRebootComm", path=path),
                path=f"{path}.AutoRebootComm",
            ),
            raw_payload=cls._preserve_raw_payload(section.raw_payload),
        )

    @classmethod
    def _build_config_heat_recovery_bypass(
        cls,
        section: ConfigSection | None,
        *,
        path: str,
    ) -> ConfigHeatRecoveryBypass | None:
        if section is None:
            return None

        return ConfigHeatRecoveryBypass(
            temp_sup_tgt_zone_1=cls._read_optional_config_value(
                section,
                "TempSupTgtZone1",
                path=path,
            ),
            temp_sup_tgt_zone_2=cls._read_optional_config_value(
                section,
                "TempSupTgtZone2",
                path=path,
            ),
            temp_sup_tgt_zone_3=cls._read_optional_config_value(
                section,
                "TempSupTgtZone3",
                path=path,
            ),
            temp_sup_tgt_zone_4=cls._read_optional_config_value(
                section,
                "TempSupTgtZone4",
                path=path,
            ),
            temp_sup_tgt_zone_5=cls._read_optional_config_value(
                section,
                "TempSupTgtZone5",
                path=path,
            ),
            temp_sup_tgt_zone_6=cls._read_optional_config_value(
                section,
                "TempSupTgtZone6",
                path=path,
            ),
            temp_sup_tgt_zone_7=cls._read_optional_config_value(
                section,
                "TempSupTgtZone7",
                path=path,
            ),
            temp_sup_tgt_zone_8=cls._read_optional_config_value(
                section,
                "TempSupTgtZone8",
                path=path,
            ),
            raw_payload=cls._preserve_raw_payload(section.raw_payload),
        )

    @classmethod
    def _build_config_heat_recovery(
        cls,
        section: ConfigSection | None,
        *,
        path: str,
    ) -> ConfigHeatRecovery | None:
        if section is None:
            return None

        return ConfigHeatRecovery(
            bypass=cls._build_config_heat_recovery_bypass(
                cls._read_optional_config_section(section, "Bypass", path=path),
                path=f"{path}.Bypass",
            ),
            raw_payload=cls._preserve_raw_payload(section.raw_payload),
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
    def _normalize_patch_model_payload(
        cls,
        payload: _PatchPayloadModel,
        *,
        path: str,
    ) -> dict[str, Any]:
        if not is_dataclass(payload):
            msg = f"Expected dataclass patch payload for {path}, got {type(payload).__name__}"
            raise ValueError(msg)

        normalized: dict[str, Any] = {}
        for model_field in fields(cast(Any, payload)):
            value = getattr(payload, model_field.name)
            if value is None:
                continue

            api_name = model_field.metadata.get("api_name")
            if not isinstance(api_name, str) or not api_name:
                msg = (
                    f"Patch model field {type(payload).__name__}.{model_field.name} "
                    "must declare api_name metadata"
                )
                raise ValueError(msg)

            item_path = f"{path}.{api_name}"

            if isinstance(value, (PatchConfigValue, PatchConfigNodeValue)):
                normalized[api_name] = {
                    "Val": cls._normalize_patch_config_scalar(value.value, path=item_path)
                }
                continue

            if isinstance(value, _PatchPayloadModel):
                normalized[api_name] = cls._normalize_patch_model_payload(value, path=item_path)
                continue

            msg = f"Unsupported patch config payload type {type(value).__name__} for {item_path}"
            raise ValueError(msg)

        return normalized

    @classmethod
    def _normalize_patch_config_payload(cls, payload: Any, *, path: str) -> dict[str, Any]:
        if isinstance(payload, _PatchPayloadModel):
            return cls._normalize_patch_model_payload(payload, path=path)

        if not isinstance(payload, dict):
            msg = f"Expected object payload for {path}, got {type(payload).__name__}"
            raise ValueError(msg)

        normalized: dict[str, Any] = {}
        for key, value in payload.items():
            if not isinstance(key, str):
                msg = f"Expected string key for {path}, got {type(key).__name__}"
                raise ValueError(msg)

            item_path = f"{path}.{key}"
            if isinstance(value, (PatchConfigValue, PatchConfigNodeValue)):
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

        return ConfigValueString(
            value=raw_value,
            raw_payload=cls._preserve_raw_payload(payload),
        )

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

        return ConfigNodeStruct(
            name=name,
            raw_payload=cls._preserve_raw_payload(payload),
        )

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
            nodes.append(
                ConfigNode(
                    node_id=node_id,
                    name=node_struct.name,
                    raw_payload=cls._preserve_raw_payload(item),
                )
            )

        return ConfigNodeOverview(
            nodes=nodes,
            raw_payload=cls._preserve_raw_payload(payload),
        )

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
        return ConfigNode(
            node_id=node_id,
            name=node_struct.name,
            raw_payload=cls._preserve_raw_payload(payload),
        )

    @classmethod
    def _parse_config_zone_string_value(
        cls,
        payload: Any,
        *,
        path: str,
    ) -> ConfigValueString:
        if not isinstance(payload, dict):
            msg = f"Expected object for zone config value {path}, got {type(payload).__name__}"
            raise DucoError(msg)

        if "Val" not in payload:
            msg = f"Expected Val in zone config value {path}"
            raise DucoError(msg)

        raw_value = payload["Val"]
        if not isinstance(raw_value, str):
            msg = (
                f"Expected string Val for zone config value {path}, got {type(raw_value).__name__}"
            )
            raise DucoError(msg)

        return ConfigValueString(
            value=raw_value,
            raw_payload=cls._preserve_raw_payload(payload),
        )

    @classmethod
    def _parse_config_group_struct(
        cls,
        payload: Any,
        *,
        path: str,
    ) -> ConfigGroupStruct:
        if not isinstance(payload, dict):
            msg = (
                f"Expected object for zone config group struct {path}, got {type(payload).__name__}"
            )
            raise DucoError(msg)

        return ConfigGroupStruct(
            raw_payload=cls._preserve_raw_payload(payload),
        )

    @classmethod
    def _parse_config_group(cls, payload: Any, *, path: str) -> ConfigGroup:
        if not isinstance(payload, dict):
            msg = f"Expected object {path}, got {type(payload).__name__}"
            raise DucoError(msg)

        if "Group" not in payload:
            msg = f"Expected integer Group in {path}"
            raise DucoError(msg)

        group_id = cls._read_scalar_value(payload, "Group")
        if type(group_id) is not int:
            msg = f"Expected integer Group in {path}, got {type(group_id).__name__}"
            raise DucoError(msg)

        cls._parse_config_group_struct(payload, path=path)
        return ConfigGroup(
            group_id=group_id,
            raw_payload=cls._preserve_raw_payload(payload),
        )

    @classmethod
    def _parse_config_zone_struct(
        cls,
        payload: Any,
        *,
        path: str,
    ) -> ConfigZoneStruct:
        if not isinstance(payload, dict):
            msg = f"Expected object for zone config struct {path}, got {type(payload).__name__}"
            raise DucoError(msg)

        name = None
        if "DeviceGroupConfig" in payload:
            device_group_config = payload["DeviceGroupConfig"]
            if not isinstance(device_group_config, dict):
                msg = f"Expected object DeviceGroupConfig in {path}"
                raise DucoError(msg)

            if "General" in device_group_config:
                general = device_group_config["General"]
                if not isinstance(general, dict):
                    msg = f"Expected object General in {path}.DeviceGroupConfig"
                    raise DucoError(msg)

                if "Name" in general:
                    name = cls._parse_config_zone_string_value(
                        general["Name"],
                        path=f"{path}.DeviceGroupConfig.General.Name",
                    )

        return ConfigZoneStruct(
            name=name,
            raw_payload=cls._preserve_raw_payload(payload),
        )

    @classmethod
    def _parse_config_zone(cls, payload: Any, *, path: str) -> ConfigZone:
        if not isinstance(payload, dict):
            msg = f"Expected object payload from {path}, got {type(payload).__name__}"
            raise DucoError(msg)

        if "Zone" not in payload:
            msg = f"Expected integer Zone in {path}"
            raise DucoError(msg)

        zone_id = cls._read_scalar_value(payload, "Zone")
        if type(zone_id) is not int:
            msg = f"Expected integer Zone in {path}, got {type(zone_id).__name__}"
            raise DucoError(msg)

        zone_struct = cls._parse_config_zone_with_group_struct(payload, path=path)
        return ConfigZone(
            zone_id=zone_id,
            name=zone_struct.name,
            groups=zone_struct.groups,
            raw_payload=cls._preserve_raw_payload(payload),
        )

    @classmethod
    def _parse_config_zone_with_group_struct(
        cls,
        payload: Any,
        *,
        path: str,
    ) -> ConfigZoneWithGroupStruct:
        if not isinstance(payload, dict):
            msg = (
                f"Expected object for zone config-with-groups struct {path}, got "
                f"{type(payload).__name__}"
            )
            raise DucoError(msg)

        zone_struct = cls._parse_config_zone_struct(payload, path=path)
        groups: list[ConfigGroup] = []
        if "Groups" in payload:
            raw_groups = payload["Groups"]
            if not isinstance(raw_groups, list):
                msg = f"Expected list Groups in {path}"
                raise DucoError(msg)

            groups = [
                cls._parse_config_group(
                    item,
                    path=f"{path}.Groups item at index {index}",
                )
                for index, item in enumerate(raw_groups)
            ]

        return ConfigZoneWithGroupStruct(
            name=zone_struct.name,
            groups=groups,
            raw_payload=cls._preserve_raw_payload(payload),
        )

    @classmethod
    def _parse_config_zones_overview(cls, payload: Any) -> ConfigZonesOverview:
        if not isinstance(payload, dict):
            msg = f"Expected object payload from /config/zones, got {type(payload).__name__}"
            raise DucoError(msg)

        if "Zones" not in payload or not isinstance(payload["Zones"], list):
            msg = "Expected list Zones in /config/zones response"
            raise DucoError(msg)

        zones: list[ConfigZone] = []
        for index, item in enumerate(payload["Zones"]):
            zones.append(
                cls._parse_config_zone(
                    item,
                    path=f"/config/zones item at index {index}",
                )
            )

        return ConfigZonesOverview(
            zones=zones,
            raw_payload=cls._preserve_raw_payload(payload),
        )

    @classmethod
    def _parse_info_group_struct(
        cls,
        payload: Any,
        *,
        path: str,
    ) -> InfoGroupStruct:
        if not isinstance(payload, dict):
            msg = f"Expected object for zone group struct {path}, got {type(payload).__name__}"
            raise DucoError(msg)

        nodes: list[int] = []
        if "DeviceGroupConfig" in payload:
            device_group_config = payload["DeviceGroupConfig"]
            if not isinstance(device_group_config, dict):
                msg = f"Expected object DeviceGroupConfig in {path}"
                raise DucoError(msg)

            if "General" in device_group_config:
                general = device_group_config["General"]
                if not isinstance(general, dict):
                    msg = f"Expected object General in {path}.DeviceGroupConfig"
                    raise DucoError(msg)

                if "Nodes" in general:
                    raw_nodes = cls._read_scalar_value(general, "Nodes")
                    if not isinstance(raw_nodes, list):
                        msg = f"Expected list Nodes in {path}.DeviceGroupConfig.General"
                        raise DucoError(msg)

                    for index, node_id in enumerate(raw_nodes):
                        if type(node_id) is not int:
                            msg = (
                                f"Expected integer node ID at {path}.DeviceGroupConfig."
                                f"General.Nodes[{index}], got {type(node_id).__name__}"
                            )
                            raise DucoError(msg)
                        nodes.append(node_id)

        return InfoGroupStruct(
            nodes=nodes,
            raw_payload=cls._preserve_raw_payload(payload),
        )

    @classmethod
    def _parse_info_group(cls, payload: Any, *, path: str) -> InfoGroup:
        if not isinstance(payload, dict):
            msg = f"Expected object {path}, got {type(payload).__name__}"
            raise DucoError(msg)

        if "Group" not in payload:
            msg = f"Expected integer Group in {path}"
            raise DucoError(msg)

        group_id = cls._read_scalar_value(payload, "Group")
        if type(group_id) is not int:
            msg = f"Expected integer Group in {path}, got {type(group_id).__name__}"
            raise DucoError(msg)

        group_struct = cls._parse_info_group_struct(payload, path=path)
        return InfoGroup(
            group_id=group_id,
            nodes=group_struct.nodes,
            raw_payload=cls._preserve_raw_payload(payload),
        )

    @classmethod
    def _parse_info_zone_group(
        cls,
        payload: Any,
        *,
        path: str,
    ) -> InfoZoneGroup:
        if not isinstance(payload, dict):
            msg = f"Expected object payload from {path}, got {type(payload).__name__}"
            raise DucoError(msg)

        if "Zone" not in payload:
            msg = f"Expected integer Zone in {path}"
            raise DucoError(msg)

        zone_id = cls._read_scalar_value(payload, "Zone")
        if type(zone_id) is not int:
            msg = f"Expected integer Zone in {path}, got {type(zone_id).__name__}"
            raise DucoError(msg)

        if "Group" not in payload:
            msg = f"Expected integer Group in {path}"
            raise DucoError(msg)

        group_id = cls._read_scalar_value(payload, "Group")
        if type(group_id) is not int:
            msg = f"Expected integer Group in {path}, got {type(group_id).__name__}"
            raise DucoError(msg)

        group_struct = cls._parse_info_group_struct(payload, path=path)
        return InfoZoneGroup(
            zone_id=zone_id,
            group_id=group_id,
            nodes=group_struct.nodes,
            raw_payload=cls._preserve_raw_payload(payload),
        )

    @classmethod
    def _parse_info_zone_struct(
        cls,
        payload: Any,
        *,
        path: str,
    ) -> InfoZoneStruct:
        if not isinstance(payload, dict):
            msg = f"Expected object for zone info struct {path}, got {type(payload).__name__}"
            raise DucoError(msg)

        name = None
        if "DeviceGroupConfig" in payload:
            device_group_config = payload["DeviceGroupConfig"]
            if not isinstance(device_group_config, dict):
                msg = f"Expected object DeviceGroupConfig in {path}"
                raise DucoError(msg)

            if "General" in device_group_config:
                general = device_group_config["General"]
                if not isinstance(general, dict):
                    msg = f"Expected object General in {path}.DeviceGroupConfig"
                    raise DucoError(msg)

                if "Name" in general:
                    raw_name = cls._read_scalar_value(general, "Name")
                    if not isinstance(raw_name, str):
                        msg = (
                            f"Expected string Name in {path}.DeviceGroupConfig.General, "
                            f"got {type(raw_name).__name__}"
                        )
                        raise DucoError(msg)
                    name = raw_name

        groups: list[InfoGroup] = []
        if "Groups" in payload:
            raw_groups = payload["Groups"]
            if not isinstance(raw_groups, list):
                msg = f"Expected list Groups in {path}"
                raise DucoError(msg)

            groups = [
                cls._parse_info_group(
                    item,
                    path=f"{path}.Groups item at index {index}",
                )
                for index, item in enumerate(raw_groups)
            ]

        return InfoZoneStruct(
            name=name,
            groups=groups,
            raw_payload=cls._preserve_raw_payload(payload),
        )

    @classmethod
    def _parse_info_zone(
        cls,
        payload: Any,
        *,
        object_context: str,
        path: str,
    ) -> InfoZone:
        if not isinstance(payload, dict):
            msg = f"Expected object {object_context}, got {type(payload).__name__}"
            raise DucoError(msg)

        if "Zone" not in payload:
            msg = f"Expected integer Zone in {path}"
            raise DucoError(msg)

        zone_id = cls._read_scalar_value(payload, "Zone")
        if type(zone_id) is not int:
            msg = f"Expected integer Zone in {path}, got {type(zone_id).__name__}"
            raise DucoError(msg)

        zone_struct = cls._parse_info_zone_struct(payload, path=path)
        return InfoZone(
            zone_id=zone_id,
            name=zone_struct.name,
            groups=zone_struct.groups,
            raw_payload=cls._preserve_raw_payload(payload),
        )

    @classmethod
    def _parse_info_zones_overview(cls, payload: Any) -> InfoZonesOverview:
        if not isinstance(payload, dict):
            msg = f"Expected object payload from /info/zones, got {type(payload).__name__}"
            raise DucoError(msg)

        if "Zones" not in payload or not isinstance(payload["Zones"], list):
            msg = "Expected list Zones in /info/zones response"
            raise DucoError(msg)

        zones: list[InfoZone] = []
        for index, item in enumerate(payload["Zones"]):
            zones.append(
                cls._parse_info_zone(
                    item,
                    object_context=(f"/info/zones item at index {index} in /info/zones response"),
                    path=f"/info/zones item at index {index}",
                )
            )

        return InfoZonesOverview(
            zones=zones,
            raw_payload=cls._preserve_raw_payload(payload),
        )

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
    def _to_action_value_type(raw_value: str) -> ActionValueType:
        try:
            return ActionValueType(raw_value)
        except ValueError:
            _LOGGER.debug(
                "Unknown action value type %r received from Duco API; falling back to UNKNOWN",
                raw_value,
            )
            return ActionValueType.UNKNOWN

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
    def _parse_action_result(
        cls,
        payload: Any,
        *,
        response_context: str = "action response",
    ) -> ActionResult:
        if not isinstance(payload, dict):
            msg = f"Expected object payload from {response_context}, got {type(payload).__name__}"
            raise DucoError(msg)

        if "Result" not in payload:
            msg = f"Expected Result in {response_context}"
            raise DucoError(msg)

        result = cls._read_scalar_value(payload, "Result")
        if not isinstance(result, str):
            msg = f"Expected string Result in {response_context}, got {type(result).__name__}"
            raise DucoError(msg)

        code: int | None = None
        if "Code" in payload:
            code = cls._read_scalar_value(payload, "Code")
            if type(code) is not int:
                msg = f"Expected integer Code in {response_context}, got {type(code).__name__}"
                raise DucoError(msg)

        message: str | None = None
        if "Message" in payload:
            message = cls._read_scalar_value(payload, "Message")
            if not isinstance(message, str):
                msg = f"Expected string Message in {response_context}, got {type(message).__name__}"
                raise DucoError(msg)

        return ActionResult(
            result=cls._to_action_result_status(result),
            code=code,
            message=message,
            raw_payload=cls._preserve_raw_payload(payload),
        )

    @classmethod
    def _parse_action_item_list(
        cls,
        payload: Any,
        *,
        response_path: str = "/action",
        item_path_prefix: str = "/action item",
    ) -> ActionItemList:
        if not isinstance(payload, list):
            msg = f"Expected list payload from {response_path}, got {type(payload).__name__}"
            raise DucoError(msg)

        return [
            cls._parse_action_item(
                item,
                path=f"{item_path_prefix} at index {index}",
                response_path=response_path,
            )
            for index, item in enumerate(payload)
        ]

    @classmethod
    def _parse_action_item(
        cls,
        payload: Any,
        *,
        path: str,
        response_path: str = "/action",
    ) -> ActionItem:
        if not isinstance(payload, dict):
            msg = (
                f"Expected object {path} in {response_path} response, got {type(payload).__name__}"
            )
            raise DucoError(msg)

        if "Action" not in payload:
            msg = f"Expected Action in {path}"
            raise DucoError(msg)

        action = cls._read_scalar_value(payload, "Action")
        if not isinstance(action, str):
            msg = f"Expected string Action in {path}, got {type(action).__name__}"
            raise DucoError(msg)

        if "ValType" not in payload:
            msg = f"Expected ValType in {path}"
            raise DucoError(msg)

        val_type = cls._read_scalar_value(payload, "ValType")
        if not isinstance(val_type, str):
            msg = f"Expected string ValType in {path}, got {type(val_type).__name__}"
            raise DucoError(msg)

        enum_values: list[str] = []
        if "Enum" in payload:
            raw_enum_values = cls._read_scalar_value(payload, "Enum")
            if not isinstance(raw_enum_values, list):
                msg = f"Expected list Enum in {path}, got {type(raw_enum_values).__name__}"
                raise DucoError(msg)

            enum_values = []
            for index, item in enumerate(raw_enum_values):
                if not isinstance(item, str):
                    msg = (
                        f"Expected string Enum value at {path}.Enum[{index}], "
                        f"got {type(item).__name__}"
                    )
                    raise DucoError(msg)
                enum_values.append(item)

        return ActionItem(
            action=action,
            val_type=cls._to_action_value_type(val_type),
            enum_values=enum_values,
            raw_payload=cls._preserve_raw_payload(payload),
        )

    @classmethod
    def _parse_node_action_item_list(
        cls,
        payload: Any,
        *,
        response_path: str = "/action/nodes",
    ) -> NodeListActionItemList:
        if not isinstance(payload, dict):
            msg = f"Expected object payload from {response_path}, got {type(payload).__name__}"
            raise DucoError(msg)

        if "Nodes" not in payload:
            msg = f"Expected Nodes in {response_path} response"
            raise DucoError(msg)

        nodes = payload["Nodes"]
        if not isinstance(nodes, list):
            msg = f"Expected list Nodes in {response_path} response, got {type(nodes).__name__}"
            raise DucoError(msg)

        return NodeListActionItemList(
            nodes=[
                cls._parse_node_action_item(
                    item,
                    path=f"{response_path} item at index {index}",
                    response_path=response_path,
                )
                for index, item in enumerate(nodes)
            ],
            raw_payload=cls._preserve_raw_payload(payload),
        )

    @classmethod
    def _parse_single_node_action_item(
        cls,
        payload: Any,
        *,
        response_path: str,
    ) -> NodeActionItemList:
        if not isinstance(payload, dict):
            msg = f"Expected object payload from {response_path}, got {type(payload).__name__}"
            raise DucoError(msg)

        return cls._parse_node_action_item(
            payload,
            path=f"{response_path} payload",
            response_path=response_path,
        )

    @classmethod
    def _parse_node_action_item(
        cls,
        payload: Any,
        *,
        path: str,
        response_path: str = "/action/nodes",
    ) -> NodeActionItemList:
        if not isinstance(payload, dict):
            msg = (
                f"Expected object {path} in {response_path} response, got {type(payload).__name__}"
            )
            raise DucoError(msg)

        if "Node" not in payload:
            msg = f"Expected Node in {path}"
            raise DucoError(msg)

        node_id = cls._read_scalar_value(payload, "Node")
        if type(node_id) is not int:
            msg = f"Expected integer Node in {path}, got {type(node_id).__name__}"
            raise DucoError(msg)

        actions: ActionItemList = []
        if "Actions" in payload:
            raw_actions = payload["Actions"]
            if not isinstance(raw_actions, list):
                msg = f"Expected list Actions in {path}, got {type(raw_actions).__name__}"
                raise DucoError(msg)

            actions = cls._parse_action_item_list(
                raw_actions,
                response_path=response_path,
                item_path_prefix=f"{path}.Actions item",
            )

        return NodeActionItemList(
            node_id=node_id,
            actions=actions,
            raw_payload=cls._preserve_raw_payload(payload),
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
                raw_payload=self._preserve_raw_payload(item),
            )
            for item in payload.get("ApiInfo", [])
        ]
        return ApiInfo(
            public_api_version=public_api_version,
            reported_api_version=reported_api_version,
            endpoints=endpoints,
            raw_payload=self._preserve_raw_payload(payload),
        )

    async def async_get_actions(self) -> ActionItemList:
        """Return supported system actions reported by the local API."""
        payload = await self._request_json("GET", "/action")
        return self._parse_action_item_list(payload)

    async def async_get_node_actions(self) -> NodeListActionItemList:
        """Return supported node actions reported by the local API."""
        payload = await self._request_json("GET", "/action/nodes")
        return self._parse_node_action_item_list(payload)

    async def async_get_node_actions_for_node(self, node_id: int) -> NodeActionItemList:
        """Return supported actions for a specific node."""
        response_path = f"/action/nodes/{node_id}"
        payload = await self._request_json("GET", response_path)
        return self._parse_single_node_action_item(payload, response_path=response_path)

    async def async_get_raw(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> Any:
        """Return the raw payload from an unmapped GET endpoint."""
        normalized_path = self._normalize_raw_get_path(path)

        if params:
            return await self._request_json("GET", normalized_path, params=params)

        return await self._request_json("GET", normalized_path)

    async def async_get_info(
        self,
        module: InfoModuleSelector | str | None = None,
        submodule: InfoGeneralSubmoduleSelector | str | None = None,
        parameter: str | None = None,
    ) -> Any:
        """Return the raw payload from the generic info endpoint."""
        params: dict[str, str] = {}
        if module is not None:
            params["module"] = str(module)
        if submodule is not None:
            params["submodule"] = str(submodule)
        if parameter is not None:
            params["parameter"] = str(parameter)

        return await self.async_get_raw("/info", params=params or None)

    async def async_get_config(
        self,
        module: ConfigModuleSelector | str | None = None,
        submodule: ConfigGeneralSubmoduleSelector
        | ConfigHeatRecoverySubmoduleSelector
        | str
        | None = None,
        parameter: str | None = None,
    ) -> Config:
        """Return configuration values from the generic config endpoint."""
        params: dict[str, str] = {}
        if module is not None:
            params["module"] = str(module)
        if submodule is not None:
            params["submodule"] = str(submodule)
        if parameter is not None:
            params["parameter"] = str(parameter)

        if params:
            payload = await self._request_json("GET", "/config", params=params)
        else:
            payload = await self._request_json("GET", "/config")

        return self._parse_config(payload)

    async def async_set_config(
        self,
        payload: dict[str, Any] | PatchConfigModel,
        module: ConfigModuleSelector | str | None = None,
        submodule: ConfigGeneralSubmoduleSelector
        | ConfigHeatRecoverySubmoduleSelector
        | str
        | None = None,
        parameter: str | None = None,
    ) -> Config:
        """Patch configuration values through the generic config endpoint."""
        params: dict[str, str] = {}
        if module is not None:
            params["module"] = str(module)
        if submodule is not None:
            params["submodule"] = str(submodule)
        if parameter is not None:
            params["parameter"] = str(parameter)

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

    async def async_get_node_configs_raw(
        self,
        parameter: str | None = None,
    ) -> Any:
        """Return the raw payload from `/config/nodes`."""
        params: dict[str, str] = {}
        if parameter is not None:
            params["parameter"] = parameter

        return await self.async_get_raw("/config/nodes", params=params or None)

    async def async_get_node_config_raw(
        self,
        node_id: int,
        parameter: str | None = None,
    ) -> Any:
        """Return the raw payload from `/config/nodes/{node}`."""
        params: dict[str, str] = {}
        if parameter is not None:
            params["parameter"] = parameter

        path = f"/config/nodes/{node_id}"
        return await self.async_get_raw(path, params=params or None)

    async def async_set_node_config_raw(
        self,
        node_id: int,
        payload: dict[str, Any],
        parameter: str | None = None,
    ) -> Any | None:
        """Patch `/config/nodes/{node}` and return the raw API payload.

        When no query parameter is requested, the Duco API may acknowledge the
        PATCH without returning a JSON body. In that case this method returns
        `None`.
        """
        params: dict[str, str] = {}
        if parameter is not None:
            params["parameter"] = parameter

        normalized_payload = self._normalize_patch_config_payload(
            payload,
            path=f"config.nodes.{node_id}",
        )

        path = f"/config/nodes/{node_id}"
        if params:
            return await self._request_json(
                "PATCH",
                path,
                params=params,
                json=normalized_payload,
                allow_empty_response=True,
            )

        return await self._request_json(
            "PATCH",
            path,
            json=normalized_payload,
            allow_empty_response=True,
        )

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

    async def async_get_zones_config(
        self,
        zone: int | None = None,
        group: int | None = None,
        module: ZoneModuleSelector | str | None = None,
        submodule: DeviceGroupConfigSubmoduleSelector | str | None = None,
        parameter: str | None = None,
    ) -> ConfigZonesOverview:
        """Return zone-level configuration values from `/config/zones`."""
        params: dict[str, str] = {}
        if zone is not None:
            params["zone"] = str(zone)
        if group is not None:
            params["group"] = str(group)
        if module is not None:
            params["module"] = str(module)
        if submodule is not None:
            params["submodule"] = str(submodule)
        if parameter is not None:
            params["parameter"] = str(parameter)

        if params:
            payload = await self._request_json("GET", "/config/zones", params=params)
        else:
            payload = await self._request_json("GET", "/config/zones")

        return self._parse_config_zones_overview(payload)

    async def async_get_zone_config(
        self,
        zone_id: int,
        group: int | None = None,
        module: ZoneModuleSelector | str | None = None,
        submodule: DeviceGroupConfigSubmoduleSelector | str | None = None,
        parameter: str | None = None,
    ) -> ConfigZone:
        """Return detailed configuration values for a specific zone."""
        params: dict[str, str] = {}
        if group is not None:
            params["group"] = str(group)
        if module is not None:
            params["module"] = str(module)
        if submodule is not None:
            params["submodule"] = str(submodule)
        if parameter is not None:
            params["parameter"] = str(parameter)

        path = f"/config/zones/{zone_id}"
        if params:
            payload = await self._request_json("GET", path, params=params)
        else:
            payload = await self._request_json("GET", path)

        return self._parse_config_zone(payload, path=path)

    async def async_set_zone_config(
        self,
        zone_id: int,
        payload: dict[str, Any] | PatchConfigZoneStruct,
        module: ZoneModuleSelector | str | None = None,
        submodule: DeviceGroupConfigSubmoduleSelector | str | None = None,
        parameter: str | None = None,
    ) -> ConfigZone:
        """Patch zone-level configuration values through `/config/zones/{zone}`."""
        params: dict[str, str] = {}
        if module is not None:
            params["module"] = str(module)
        if submodule is not None:
            params["submodule"] = str(submodule)
        if parameter is not None:
            params["parameter"] = str(parameter)

        normalized_payload = self._normalize_patch_config_payload(
            payload,
            path=f"config.zones.{zone_id}",
        )

        path = f"/config/zones/{zone_id}"
        if params:
            response = await self._request_json(
                "PATCH",
                path,
                params=params,
                json=normalized_payload,
            )
        else:
            response = await self._request_json(
                "PATCH",
                path,
                json=normalized_payload,
            )

        return self._parse_config_zone(response, path=path)

    async def async_set_node_config(
        self,
        node_id: int,
        payload: dict[str, Any] | PatchConfigNodeStruct,
        parameter: Literal["Name"] = "Name",
    ) -> ConfigNode:
        """Patch node-level configuration values through `/config/nodes/{node}`.

        The Duco API returns no node payload for this PATCH endpoint when no
        query parameter is requested, so the typed writer always targets the
        `Name` field that is covered by the current node config models.
        """
        if parameter != "Name":
            msg = "async_set_node_config only supports parameter='Name'"
            raise ValueError(msg)

        # Keep the return type stable: without `parameter=Name`, this endpoint
        # may succeed without returning a node payload that can be parsed.
        params = {"parameter": parameter}

        normalized_payload = self._normalize_patch_config_payload(
            payload,
            path=f"config.nodes.{node_id}",
        )

        path = f"/config/nodes/{node_id}"
        response = await self._request_json(
            "PATCH",
            path,
            params=params,
            json=normalized_payload,
        )

        return self._parse_config_node(response, path=path)

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
            raw_payload=self._preserve_raw_payload(board),
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
            raw_payload=self._preserve_raw_payload(lan),
        )

    @classmethod
    def _parse_diag_component(cls, payload: Any, *, path: str) -> DiagComponent | None:
        if not isinstance(payload, dict):
            _LOGGER.debug(
                "Skipping diagnostic subsystem at %s: expected object, got %s",
                path,
                type(payload).__name__,
            )
            return None

        component = payload.get("Component")
        status = payload.get("Status")
        if not isinstance(component, str) or not component:
            _LOGGER.debug(
                "Skipping diagnostic subsystem at %s: missing non-empty string Component",
                path,
            )
            return None
        if not isinstance(status, str) or not status:
            _LOGGER.debug(
                "Skipping diagnostic subsystem at %s: missing non-empty string Status",
                path,
            )
            return None

        return DiagComponent(
            component=component,
            status=status,
            raw_payload=cls._preserve_raw_payload(payload),
        )

    @classmethod
    def _parse_diag_info(cls, payload: Any) -> DiagInfo:
        if not isinstance(payload, dict):
            msg = f"Expected object payload from /info?module=Diag, got {type(payload).__name__}"
            raise DucoError(msg)

        diag_payload = payload.get("Diag")
        if diag_payload is None:
            return DiagInfo()
        if not isinstance(diag_payload, dict):
            msg = f"Expected object for Diag, got {type(diag_payload).__name__}"
            raise DucoError(msg)

        raw_subsystems = diag_payload.get("SubSystems")
        if raw_subsystems is None:
            return DiagInfo(raw_payload=cls._preserve_raw_payload(diag_payload))
        if not isinstance(raw_subsystems, list):
            msg = f"Expected list for Diag.SubSystems, got {type(raw_subsystems).__name__}"
            raise DucoError(msg)

        diagnostic_subsystems: list[DiagComponent] = []
        for index, item in enumerate(raw_subsystems):
            subsystem = cls._parse_diag_component(item, path=f"Diag.SubSystems[{index}]")
            if subsystem is not None:
                diagnostic_subsystems.append(subsystem)

        return DiagInfo(
            diagnostic_subsystems=tuple(diagnostic_subsystems),
            raw_payload=cls._preserve_raw_payload(diag_payload),
        )

    async def async_get_diagnostics_info(self) -> DiagInfo:
        """Return diagnostic subsystem details reported by the box."""
        payload = await self.async_get_info(module="Diag")
        return self._parse_diag_info(payload)

    async def async_get_diagnostics(self) -> list[DiagComponent]:
        """Return health states for diagnostic subsystems."""
        return list((await self.async_get_diagnostics_info()).diagnostic_subsystems)

    async def async_get_nodes(self) -> list[Node]:
        """Return nodes reported by the local API."""
        payload = await self._request_json("GET", "/info/nodes")
        return [self._parse_node(item) for item in payload["Nodes"]]

    async def async_get_zones_info(self) -> InfoZonesOverview:
        """Return zone information reported by the local API."""
        payload = await self._request_json("GET", "/info/zones")
        return self._parse_info_zones_overview(payload)

    async def async_get_zone_info(
        self,
        zone_id: int,
        group: int | None = None,
        module: ZoneModuleSelector | str | None = None,
        submodule: DeviceGroupConfigSubmoduleSelector | str | None = None,
        parameter: str | None = None,
    ) -> InfoZone:
        """Return detailed information for a specific zone."""
        params: dict[str, str] = {}
        if group is not None:
            params["group"] = str(group)
        if module is not None:
            params["module"] = str(module)
        if submodule is not None:
            params["submodule"] = str(submodule)
        if parameter is not None:
            params["parameter"] = str(parameter)

        if params:
            payload = await self._request_json(
                "GET",
                f"/info/zones/{zone_id}",
                params=params,
            )
        else:
            payload = await self._request_json("GET", f"/info/zones/{zone_id}")

        return self._parse_info_zone(
            payload,
            object_context=f"payload from /info/zones/{zone_id}",
            path=f"/info/zones/{zone_id}",
        )

    async def async_get_zone_group_info(
        self,
        zone_id: int,
        group_id: int,
        module: ZoneModuleSelector | str | None = None,
        submodule: DeviceGroupConfigSubmoduleSelector | str | None = None,
        parameter: str | None = None,
    ) -> InfoZoneGroup:
        """Return detailed information for a specific zone group."""
        params: dict[str, str] = {}
        if module is not None:
            params["module"] = str(module)
        if submodule is not None:
            params["submodule"] = str(submodule)
        if parameter is not None:
            params["parameter"] = str(parameter)

        path = f"/info/zones/{zone_id}/groups/{group_id}"
        if params:
            payload = await self._request_json("GET", path, params=params)
        else:
            payload = await self._request_json("GET", path)

        return self._parse_info_zone_group(payload, path=path)

    async def async_get_nodes_overview(self) -> list[NodeOverview]:
        """Return lightweight node identifiers reported by the local API."""
        payload = await self._request_json("GET", "/nodes")
        return self._parse_nodes_overview(payload)

    async def async_get_node_info(
        self,
        node_id: int,
        module: NodeInfoModuleSelector | str | None = None,
        parameter: str | None = None,
    ) -> Node:
        """Return detailed information for a specific node."""
        params: dict[str, str] = {}
        if module is not None:
            params["module"] = str(module)
        if parameter is not None:
            params["parameter"] = str(parameter)

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

    async def async_get_time_filter_remaining(self) -> int | None:
        """Return the remaining heat recovery filter time when the box reports it."""
        try:
            payload = await self.async_get_info(module=InfoModuleSelector.HEAT_RECOVERY)
        except DucoResponseError as err:
            if _is_unsupported_optional_endpoint_error(err, "/info"):
                raise DucoUnsupportedCapabilityError(
                    err.status,
                    err.path,
                    err.body,
                ) from err
            raise

        if not isinstance(payload, dict):
            msg = (
                "Expected object payload from /info?module=HeatRecovery, got "
                f"{type(payload).__name__}"
            )
            raise DucoError(msg)

        heat_recovery = payload.get("HeatRecovery")
        if heat_recovery is None:
            return None
        if not isinstance(heat_recovery, dict):
            msg = "Expected object payload at HeatRecovery in /info?module=HeatRecovery response"
            raise DucoError(msg)

        general = heat_recovery.get("General")
        if general is None:
            return None
        if not isinstance(general, dict):
            msg = (
                "Expected object payload at HeatRecovery.General in "
                "/info?module=HeatRecovery response"
            )
            raise DucoError(msg)

        return self._read_optional_wrapped_int(
            general,
            "TimeFilterRemain",
            path="HeatRecovery.General",
        )

    async def async_get_ventilation_temperature_info(self) -> VentilationTemperatureInfo:
        """Return ventilation temperatures when the box exposes them, in Celsius."""
        try:
            payload = await self.async_get_info(module=InfoModuleSelector.VENTILATION)
        except DucoResponseError as err:
            if _is_unsupported_optional_endpoint_error(err, "/info"):
                raise DucoUnsupportedCapabilityError(
                    err.status,
                    err.path,
                    err.body,
                ) from err
            raise

        if not isinstance(payload, dict):
            msg = (
                "Expected object payload from /info?module=Ventilation, got "
                f"{type(payload).__name__}"
            )
            raise DucoError(msg)

        ventilation = payload.get("Ventilation")
        if ventilation is None:
            return VentilationTemperatureInfo()
        if not isinstance(ventilation, dict):
            msg = "Expected object payload at Ventilation in /info?module=Ventilation response"
            raise DucoError(msg)

        sensor = ventilation.get("Sensor")
        if sensor is None:
            return VentilationTemperatureInfo(raw_payload=self._preserve_raw_payload(ventilation))
        if not isinstance(sensor, dict):
            msg = (
                "Expected object payload at Ventilation.Sensor in /info?module=Ventilation response"
            )
            raise DucoError(msg)

        temp_oda = self._read_optional_wrapped_int(sensor, "TempOda", path="Ventilation.Sensor")
        temp_sup = self._read_optional_wrapped_int(sensor, "TempSup", path="Ventilation.Sensor")
        temp_eta = self._read_optional_wrapped_int(sensor, "TempEta", path="Ventilation.Sensor")
        temp_eha = self._read_optional_wrapped_int(sensor, "TempEha", path="Ventilation.Sensor")

        return VentilationTemperatureInfo(
            temp_oda=None if temp_oda is None else self._decicelsius_to_celsius(temp_oda),
            temp_sup=None if temp_sup is None else self._decicelsius_to_celsius(temp_sup),
            temp_eta=None if temp_eta is None else self._decicelsius_to_celsius(temp_eta),
            temp_eha=None if temp_eha is None else self._decicelsius_to_celsius(temp_eha),
            raw_payload=self._preserve_raw_payload(sensor),
        )

    async def async_get_bypass_supply_temperature_target(
        self,
        zone_id: int,
    ) -> BypassSupplyTemperatureTarget | None:
        """Return a bypass supply target from `/config` in Celsius."""
        parameter = self._validate_bypass_zone_id(zone_id)
        try:
            config = await self.async_get_config(
                module=ConfigModuleSelector.HEAT_RECOVERY,
                submodule=ConfigHeatRecoverySubmoduleSelector.BYPASS,
                parameter=parameter,
            )
        except DucoResponseError as err:
            if _is_unsupported_optional_endpoint_error(err, "/config"):
                raise DucoUnsupportedCapabilityError(
                    err.status,
                    err.path,
                    err.body,
                ) from err
            raise
        return self._extract_bypass_supply_temperature_target(config, zone_id)

    async def async_set_bypass_supply_temperature_target(
        self,
        zone_id: int,
        temperature: float,
    ) -> BypassSupplyTemperatureTarget:
        """Set a bypass supply target through `/config` using Celsius input."""
        parameter = self._validate_bypass_zone_id(zone_id)
        raw_value = self._celsius_to_decicelsius(
            temperature,
            path=f"bypass_supply_temperature_target[{zone_id}]",
        )
        response = await self.async_set_config(
            {"HeatRecovery": {"Bypass": {parameter: PatchConfigValue(value=raw_value)}}},
            module=ConfigModuleSelector.HEAT_RECOVERY,
            submodule=ConfigHeatRecoverySubmoduleSelector.BYPASS,
            parameter=parameter,
        )
        target = self._extract_bypass_supply_temperature_target(response, zone_id)
        if target is None:
            msg = f"Expected {parameter} in /config response after bypass target write"
            raise DucoError(msg)
        return target

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

    async def async_set_action(
        self,
        action: ActionName | str,
        val: str | int | bool | None = None,
    ) -> ActionResult:
        """Execute a generic system action through the local Duco API."""
        payload: dict[str, str | int | bool] = {"Action": action}
        if val is not None:
            payload["Val"] = val

        response = await self._request_json(
            "POST",
            "/action",
            json=payload,
        )
        return self._parse_action_result(response, response_context="system action response")

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
        action: ActionName | str,
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
        return self._parse_action_result(response, response_context="node action response")

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
            raw_payload=self._preserve_raw_payload(general),
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
                raw_payload=self._preserve_raw_payload(vent),
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
                raw_payload=self._preserve_raw_payload(sensor_payload),
            )

        motor_state = None
        if "MotorStateCtrl" in payload:
            motor_payload = payload["MotorStateCtrl"]
            motor_state = NodeMotorStateInfo(
                device_type=self._read_wrapped_value(motor_payload, "DeviceType")
                if "DeviceType" in motor_payload
                else None,
                req=self._read_wrapped_value(motor_payload, "Req")
                if "Req" in motor_payload
                else None,
                pos_req=self._read_wrapped_value(motor_payload, "PosReq")
                if "PosReq" in motor_payload
                else None,
                pos=self._read_wrapped_value(motor_payload, "Pos")
                if "Pos" in motor_payload
                else None,
                raw_payload=self._preserve_raw_payload(motor_payload),
            )

        return Node(
            node_id=payload["Node"],
            general=node_general,
            ventilation=ventilation,
            sensor=sensor,
            motor_state=motor_state,
            raw_payload=self._preserve_raw_payload(payload),
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

            nodes.append(
                NodeOverview(
                    node_id=node_id,
                    raw_payload=cls._preserve_raw_payload(item),
                )
            )

        return nodes
