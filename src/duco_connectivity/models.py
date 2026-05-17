"""Typed models for values exposed by the local Duco API."""

import logging
import re
import sys
from dataclasses import dataclass, field
from enum import StrEnum
from types import FrameType
from typing import Any, Self

_LOGGER = logging.getLogger(__name__)
_VERSION_PATTERN = re.compile(r"^\d+(?:\.\d+)*$")


def _compat_caller() -> str | None:
    """Return the first external caller that reached a compatibility path."""
    frame: FrameType | None = sys._getframe(1)

    while frame is not None:
        module_name = frame.f_globals.get("__name__", "")
        if module_name != "duco_connectivity" and not module_name.startswith("duco_connectivity."):
            return f"{module_name}.{frame.f_code.co_name}"
        frame = frame.f_back

    return None


class KnownBoardName(StrEnum):
    """Observed stable board identity values exposed through `BoxName`."""

    ENERGY = "ENERGY"
    FOCUS = "FOCUS"
    SILENT_CONNECT = "SILENT_CONNECT"


class BoardName(str):
    """String-compatible board identity with optional known-value matching."""

    def __new__(cls, value: str) -> Self:
        return super().__new__(cls, value)

    @property
    def known_value(self) -> KnownBoardName | None:
        """Return the matched known board identity when available."""
        try:
            return KnownBoardName(self)
        except ValueError:
            return None

    @property
    def is_known(self) -> bool:
        """Return whether the board identity matches a known stable value."""
        return self.known_value is not None


class DucoVersion(str):
    """String-compatible Duco version value with parsed numeric components."""

    def __new__(cls, value: str) -> Self:
        return super().__new__(cls, value)

    @property
    def components(self) -> tuple[int, ...] | None:
        """Return parsed integer version components when the value is numeric."""
        if not _VERSION_PATTERN.fullmatch(self):
            return None
        return tuple(int(part) for part in self.split("."))

    @property
    def is_well_formed(self) -> bool:
        """Return whether the version matches the numeric dotted format."""
        return self.components is not None

    @property
    def major(self) -> int | None:
        """Return the first parsed version component when available."""
        components = self.components
        if components is None:
            return None
        return components[0]

    @property
    def minor(self) -> int | None:
        """Return the second parsed version component when available."""
        components = self.components
        if components is None or len(components) < 2:
            return None
        return components[1]


class DucoSerialNumber(str):
    """String-compatible serial identifier reported by the Duco API."""

    def __new__(cls, value: str) -> Self:
        return super().__new__(cls, value)


class IpAddress(str):
    """String-compatible IP-like metadata value reported by the Duco API."""

    def __new__(cls, value: str) -> Self:
        return super().__new__(cls, value)


class MacAddress(str):
    """String-compatible MAC address value reported by the Duco API."""

    def __new__(cls, value: str) -> Self:
        return super().__new__(cls, value)


class HostName(str):
    """String-compatible host name value reported by the Duco API."""

    def __new__(cls, value: str) -> Self:
        return super().__new__(cls, value)


class KnownLanMode(StrEnum):
    """Observed stable LAN mode values exposed through `Lan.Mode`."""

    NO_CONNECTION = "NO_CONNECTION"
    WIFI_AP = "WIFI_AP"
    WIFI_CLIENT = "WIFI_CLIENT"
    ETHERNET = "ETHERNET"


class LanMode(str):
    """String-compatible LAN mode with optional known-value matching."""

    def __new__(cls, value: str) -> Self:
        return super().__new__(cls, value)

    @property
    def known_value(self) -> KnownLanMode | None:
        """Return the matched known LAN mode when available."""
        try:
            return KnownLanMode(self)
        except ValueError:
            return None

    @property
    def is_known(self) -> bool:
        """Return whether the LAN mode matches a known stable value."""
        return self.known_value is not None


def _coerce_board_name(value: BoardName | str) -> BoardName:
    """Normalize public board identity values to `BoardName`."""
    if isinstance(value, BoardName):
        return value
    return BoardName(value)


def _coerce_duco_version(value: DucoVersion | str) -> DucoVersion:
    """Normalize public version values to `DucoVersion`."""
    if isinstance(value, DucoVersion):
        return value
    return DucoVersion(value)


def _coerce_duco_serial_number(value: DucoSerialNumber | str) -> DucoSerialNumber:
    """Normalize public serial values to `DucoSerialNumber`."""
    if isinstance(value, DucoSerialNumber):
        return value
    return DucoSerialNumber(value)


def _coerce_ip_address(value: IpAddress | str) -> IpAddress:
    """Normalize public IP-like values to `IpAddress`."""
    if isinstance(value, IpAddress):
        return value
    return IpAddress(value)


def _coerce_mac_address(value: MacAddress | str) -> MacAddress:
    """Normalize public MAC values to `MacAddress`."""
    if isinstance(value, MacAddress):
        return value
    return MacAddress(value)


def _coerce_host_name(value: HostName | str) -> HostName:
    """Normalize public host name values to `HostName`."""
    if isinstance(value, HostName):
        return value
    return HostName(value)


def _coerce_lan_mode(value: LanMode | str) -> LanMode:
    """Normalize public LAN mode values to `LanMode`."""
    if isinstance(value, LanMode):
        return value
    return LanMode(value)


class NodeType(StrEnum):
    """Node categories reported by the API.

    `UNKN` is an API-defined value, while `UNKNOWN` is the client fallback for
    unmapped future values.
    """

    UNKN = "UNKN"
    IQ = "IQ"
    CO2 = "CO2"
    RH = "RH"
    KLEP = "KLEP"
    TOP = "TOP"
    COMB = "COMB"
    CLIMA = "CLIMA"
    UCBAT = "UCBAT"
    UC = "UC"
    UCRH = "UCRH"
    UCVOC = "UCVOC"
    UCCO2 = "UCCO2"
    UCSUN = "UCSUN"
    UCVENT = "UCVENT"
    VLV = "VLV"
    VLVRH = "VLVRH"
    VLVVOC = "VLVVOC"
    VLVCO2 = "VLVCO2"
    BOX = "BOX"
    SWITCH = "SWITCH"
    ACTUAT = "ACTUAT"
    UCBATRH = "UCBATRH"
    PWMIN = "PWMIN"
    IAV = "IAV"
    IAVRH = "IAVRH"
    IAVVOC = "IAVVOC"
    IAVCO2 = "IAVCO2"
    EAV = "EAV"
    EAVRH = "EAVRH"
    EAVVOC = "EAVVOC"
    EAVCO2 = "EAVCO2"
    BOIILER = "BOIILER"
    TRONIC = "TRONIC"
    VLVCO2RH = "VLVCO2RH"
    BSCO2 = "BSCO2"
    BSRH = "BSRH"
    BSVOC = "BSVOC"
    MOTORRLY = "MOTORRLY"
    MOTORMB = "MOTORMB"
    WXSENSOR = "WXSENSOR"
    DI = "DI"
    DO = "DO"
    COMM = "COMM"
    RLYMB = "RLYMB"
    PERILEX = "PERILEX"
    RO = "RO"
    UNKNOWN = "UNKNOWN"


class NetworkType(StrEnum):
    """Transport types reported for node connectivity."""

    NONE = "-"
    VIRT = "VIRT"
    RF = "RF"
    WI = "WI"
    MB = "MB"
    UNKNOWN = "UNKNOWN"


class VentilationMode(StrEnum):
    """Control modes reported for node ventilation, plus a client-side fallback."""

    NONE = "-"
    AUTO = "AUTO"
    MANU = "MANU"
    OVRL = "OVRL"
    EXTN = "EXTN"
    COOL = "COOL"
    NA = "N/A"
    DSBL = "DSBL"
    UNKNOWN = "UNKNOWN"


class VentilationState(StrEnum):
    """Ventilation states reported by the API, plus compatibility and fallback values.

    The public API notes explicitly define the base AUTO/AUT*/MAN*/EMPT/CNT*
    values plus `-`. Timed manual variants are retained as compatibility
    members because they have appeared in observed payloads and Duco action
    discovery responses.
    """

    AUTO = "AUTO"
    AUT1 = "AUT1"
    AUT2 = "AUT2"
    AUT3 = "AUT3"
    MAN1 = "MAN1"
    MAN2 = "MAN2"
    MAN3 = "MAN3"
    EMPT = "EMPT"
    CNT1 = "CNT1"
    CNT2 = "CNT2"
    CNT3 = "CNT3"
    NONE = "-"
    MAN1x2 = "MAN1x2"
    MAN2x2 = "MAN2x2"
    MAN3x2 = "MAN3x2"
    MAN1x3 = "MAN1x3"
    MAN2x3 = "MAN2x3"
    MAN3x3 = "MAN3x3"
    UNKNOWN = "UNKNOWN"


class DiagStatus(StrEnum):
    """Health states returned by the diagnostics API, plus a client-side fallback."""

    OK = "Ok"
    DISABLE = "Disable"
    ERROR = "Error"
    UNKNOWN = "UNKNOWN"


class ActionResultStatus(StrEnum):
    """Status values returned by node action execution, plus a client-side fallback."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class ActionValueType(StrEnum):
    """Value kinds reported for action discovery, plus a client-side fallback."""

    NONE = "None"
    BOOLEAN = "Boolean"
    INTEGER = "Integer"
    STRING = "String"
    ENUM = "Enum"
    UNKNOWN = "UNKNOWN"


class InfoModuleSelector(StrEnum):
    """Known stable module selectors for the generic `/info` endpoint.

    These values come from the published Duco public API notes and the typed
    reader families already exposed by this library. Generic info readers keep
    accepting raw strings alongside these enums for forward compatibility.
    """

    GENERAL = "General"
    DIAG = "Diag"
    VENTILATION = "Ventilation"
    HEAT_RECOVERY = "HeatRecovery"
    WEATHER_HANDLER = "WeatherHandler"


class InfoGeneralSubmoduleSelector(StrEnum):
    """Known stable `General` submodule selectors for `/info`."""

    BOARD = "Board"
    LAN = "Lan"
    PUBLIC_API = "PublicApi"
    MODBUS = "Modbus"


class ConfigModuleSelector(StrEnum):
    """Known stable module selectors for the generic `/config` endpoint."""

    GENERAL = "General"
    HEAT_RECOVERY = "HeatRecovery"


class ConfigGeneralSubmoduleSelector(StrEnum):
    """Known stable `General` submodule selectors for `/config`."""

    TIME = "Time"
    MODBUS = "Modbus"
    LAN = "Lan"
    AUTO_REBOOT_COMM = "AutoRebootComm"


class ConfigHeatRecoverySubmoduleSelector(StrEnum):
    """Known stable `HeatRecovery` submodule selectors for `/config`."""

    BYPASS = "Bypass"


class NodeInfoModuleSelector(StrEnum):
    """Known stable module selectors for `/info/nodes/{node}`."""

    GENERAL = "General"
    VENTILATION = "Ventilation"
    SENSOR = "Sensor"
    MOTOR_STATE_CTRL = "MotorStateCtrl"


class ZoneModuleSelector(StrEnum):
    """Known stable module selectors for zone info and config endpoints."""

    DEVICE_GROUP_CONFIG = "DeviceGroupConfig"


class DeviceGroupConfigSubmoduleSelector(StrEnum):
    """Known stable `DeviceGroupConfig` submodule selectors for zone endpoints."""

    GENERAL = "General"


@dataclass(frozen=True, slots=True)
class ApiEndpoint:
    """Capabilities advertised for a single API endpoint."""

    url: str
    methods: list[str] = field(default_factory=list)
    query_parameters: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True, init=False)
class ApiInfo:
    """Version and endpoint metadata returned by the API root."""

    public_api_version: DucoVersion
    reported_api_version: str | None = None
    endpoints: list[ApiEndpoint] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def __init__(
        self,
        public_api_version: DucoVersion | str | None = None,
        reported_api_version: str | None = None,
        endpoints: list[ApiEndpoint] | None = None,
        *,
        api_version: DucoVersion | str | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> None:
        """Initialize API info with backward-compatible api_version support."""
        if api_version is not None:
            caller = _compat_caller()
            if caller is None:
                _LOGGER.debug(
                    "Compatibility constructor argument api_version used; "
                    "mapping to public_api_version."
                )
            else:
                _LOGGER.debug(
                    "Compatibility constructor argument api_version used by %s; "
                    "mapping to public_api_version.",
                    caller,
                )

        resolved_public_api_version = public_api_version
        if resolved_public_api_version is None:
            resolved_public_api_version = api_version
        elif api_version is not None and api_version != public_api_version:
            msg = "api_version must match public_api_version when both are provided"
            raise ValueError(msg)

        if resolved_public_api_version is None:
            msg = "public_api_version or api_version must be provided"
            raise TypeError(msg)

        object.__setattr__(
            self,
            "public_api_version",
            _coerce_duco_version(resolved_public_api_version),
        )
        object.__setattr__(self, "reported_api_version", reported_api_version)
        object.__setattr__(self, "endpoints", [] if endpoints is None else endpoints)
        object.__setattr__(self, "raw_payload", {} if raw_payload is None else raw_payload)

    @property
    def api_version(self) -> DucoVersion:
        """Backward-compatible alias for the old api_version field name."""
        caller = _compat_caller()
        if caller is None:
            _LOGGER.debug(
                "Compatibility property api_version accessed; delegating to public_api_version."
            )
        else:
            _LOGGER.debug(
                "Compatibility property api_version accessed by %s; delegating to "
                "public_api_version.",
                caller,
            )
        return self.public_api_version


ApiEndpointInfo = ApiEndpoint


@dataclass(frozen=True, slots=True, init=False)
class BoardInfo:
    """Identity and version fields for the main Duco unit."""

    box_name: BoardName
    box_sub_type_name: str
    serial_board_box: DucoSerialNumber
    serial_board_comm: DucoSerialNumber
    serial_duco_box: DucoSerialNumber
    serial_duco_comm: DucoSerialNumber
    time: int
    public_api_version: DucoVersion | None = None
    software_version: DucoVersion | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def __init__(
        self,
        box_name: BoardName | str,
        box_sub_type_name: str,
        serial_board_box: DucoSerialNumber | str,
        serial_board_comm: DucoSerialNumber | str,
        serial_duco_box: DucoSerialNumber | str,
        serial_duco_comm: DucoSerialNumber | str,
        time: int,
        public_api_version: DucoVersion | str | None = None,
        software_version: DucoVersion | str | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> None:
        """Initialize board info with compatibility-friendly constructor types."""
        object.__setattr__(self, "box_name", _coerce_board_name(box_name))
        object.__setattr__(self, "box_sub_type_name", box_sub_type_name)
        object.__setattr__(
            self,
            "serial_board_box",
            _coerce_duco_serial_number(serial_board_box),
        )
        object.__setattr__(
            self,
            "serial_board_comm",
            _coerce_duco_serial_number(serial_board_comm),
        )
        object.__setattr__(
            self,
            "serial_duco_box",
            _coerce_duco_serial_number(serial_duco_box),
        )
        object.__setattr__(
            self,
            "serial_duco_comm",
            _coerce_duco_serial_number(serial_duco_comm),
        )
        object.__setattr__(self, "time", time)
        object.__setattr__(
            self,
            "public_api_version",
            None if public_api_version is None else _coerce_duco_version(public_api_version),
        )
        object.__setattr__(
            self,
            "software_version",
            None if software_version is None else _coerce_duco_version(software_version),
        )
        object.__setattr__(self, "raw_payload", {} if raw_payload is None else raw_payload)


@dataclass(frozen=True, slots=True, init=False)
class LanInfo:
    """LAN settings reported by the main unit."""

    mode: LanMode
    ip: IpAddress
    net_mask: IpAddress
    default_gateway: IpAddress
    dns: IpAddress
    mac: MacAddress
    host_name: HostName
    rssi_wifi: int | None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def __init__(
        self,
        mode: LanMode | str,
        ip: IpAddress | str,
        net_mask: IpAddress | str,
        default_gateway: IpAddress | str,
        dns: IpAddress | str,
        mac: MacAddress | str,
        host_name: HostName | str,
        rssi_wifi: int | None,
        raw_payload: dict[str, Any] | None = None,
    ) -> None:
        """Initialize LAN info with compatibility-friendly constructor types."""
        object.__setattr__(self, "mode", _coerce_lan_mode(mode))
        object.__setattr__(self, "ip", _coerce_ip_address(ip))
        object.__setattr__(self, "net_mask", _coerce_ip_address(net_mask))
        object.__setattr__(self, "default_gateway", _coerce_ip_address(default_gateway))
        object.__setattr__(self, "dns", _coerce_ip_address(dns))
        object.__setattr__(self, "mac", _coerce_mac_address(mac))
        object.__setattr__(self, "host_name", _coerce_host_name(host_name))
        object.__setattr__(self, "rssi_wifi", rssi_wifi)
        object.__setattr__(self, "raw_payload", {} if raw_payload is None else raw_payload)


@dataclass(frozen=True, slots=True)
class ConfigValue:
    """Integer config value reported by the local Duco API."""

    value: int
    minimum: int | None = None
    increment: int | None = None
    maximum: int | None = None
    options: tuple[int, ...] | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class ConfigValueOptions(ConfigValue):
    """Integer config value with an explicit option list."""

    options: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class ConfigValueString:
    """String config value reported by the local Duco API."""

    value: str
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class ConfigSection:
    """Nested config section returned by the local Duco API."""

    entries: dict[str, "ConfigItem"] = field(default_factory=dict)
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


type ConfigItem = ConfigSection | ConfigValue | ConfigValueOptions | ConfigValueString


@dataclass(frozen=True, slots=True)
class Config:
    """Top-level config payload returned by the local Duco API."""

    sections: dict[str, ConfigSection] = field(default_factory=dict)
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class ConfigNodeStruct:
    """Writable or readable node config fields."""

    name: ConfigValueString | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class ConfigNode:
    """Node-scoped config payload returned by the local Duco API."""

    node_id: int
    name: ConfigValueString | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class ConfigNodeOverview:
    """Collection of node-scoped config payloads."""

    nodes: list[ConfigNode] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True, eq=False)
class ConfigGroupStruct:
    """Group-level zone config fields returned by the local Duco API."""

    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class ConfigGroup:
    """Zone config group entry returned by the local Duco API."""

    group_id: int
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class ConfigZoneStruct:
    """Writable or readable zone config fields."""

    name: ConfigValueString | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class ConfigZone:
    """Zone-scoped config payload returned by the local Duco API."""

    zone_id: int
    name: ConfigValueString | None = None
    groups: list[ConfigGroup] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class ConfigZonesOverview:
    """Collection of zone-scoped config payloads."""

    zones: list[ConfigZone] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class PatchConfigValue:
    """Leaf config payload used by generic config write methods."""

    value: int | str


@dataclass(frozen=True, slots=True)
class InfoGroupStruct:
    """Group membership fields returned by the local Duco API."""

    nodes: list[int] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class InfoGroup:
    """Zone group entry returned by the local Duco API."""

    group_id: int
    nodes: list[int] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class InfoZoneGroup:
    """Group-scoped zone info payload returned by the local Duco API."""

    zone_id: int
    group_id: int
    nodes: list[int] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class InfoZoneStruct:
    """Zone info fields returned by the local Duco API."""

    name: str | None = None
    groups: list[InfoGroup] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class InfoZone:
    """Zone entry returned by the local Duco API."""

    zone_id: int
    name: str | None = None
    groups: list[InfoGroup] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class InfoZonesOverview:
    """Collection of zone info payloads."""

    zones: list[InfoZone] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class PatchConfigNodeValue:
    """Leaf node config payload used by future node config write methods."""

    value: int | str


@dataclass(frozen=True, slots=True)
class NodeSensorInfo:
    """Sensor readings reported for a node."""

    co2: int | None = None
    iaq_co2: int | None = None
    rh: float | None = None
    iaq_rh: int | None = None
    temp: float | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class NodeMotorStateInfo:
    """Motor controller state reported for a node."""

    device_type: int | None = None
    req: int | None = None
    pos_req: int | None = None
    pos: int | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class NodeVentilationInfo:
    """Ventilation state and timers reported for a node."""

    state: VentilationState
    mode: VentilationMode
    time_state_remain: int
    time_state_end: int
    flow_lvl_tgt: int | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class NodeGeneralInfo:
    """Static node metadata used to identify a device."""

    node_type: NodeType
    sub_type: int
    network_type: NetworkType
    parent: int
    asso: int
    name: str
    identify: int
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class Node:
    """Node returned by the local Duco API."""

    node_id: int
    general: NodeGeneralInfo
    ventilation: NodeVentilationInfo | None = None
    sensor: NodeSensorInfo | None = None
    motor_state: NodeMotorStateInfo | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class NodeOverview:
    """Lightweight node identifier returned by the local Duco API."""

    node_id: int
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class DiagComponent:
    """Health state for a diagnostic subsystem."""

    component: str
    status: DiagStatus
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class Action:
    """System action request payload."""

    action: str
    val: str | int | bool | None = None


@dataclass(frozen=True, slots=True)
class ActionNode:
    """Node action request payload."""

    action: str
    val: str | int | bool | None = None


@dataclass(frozen=True, slots=True)
class ActionItem:
    """Action definition returned by action discovery endpoints."""

    action: str
    val_type: ActionValueType
    enum_values: list[str] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


type ActionItemList = list[ActionItem]


@dataclass(frozen=True, slots=True)
class NodeActionItemList:
    """Node-scoped action discovery entry."""

    node_id: int
    actions: list[ActionItem] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class NodeListActionItemList:
    """Collection of node-scoped action discovery entries."""

    nodes: list[NodeActionItemList] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class ActionResult:
    """Outcome returned by an action execution request."""

    result: ActionResultStatus
    code: int | None = None
    message: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
