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


class NodeSubtype(int):
    """Integer-compatible node subtype value reported by the API."""

    def __new__(cls, value: int) -> Self:
        return super().__new__(cls, value)


class NodeParentId(int):
    """Integer-compatible parent node identifier reported by the API."""

    def __new__(cls, value: int) -> Self:
        return super().__new__(cls, value)


class NodeAssociationId(int):
    """Integer-compatible associated node identifier reported by the API."""

    def __new__(cls, value: int) -> Self:
        return super().__new__(cls, value)


class NodeName(str):
    """String-compatible node name value reported by the API."""

    def __new__(cls, value: str) -> Self:
        return super().__new__(cls, value)


class NodeIdentify(int):
    """Integer-compatible identify state value reported by the API."""

    def __new__(cls, value: int) -> Self:
        return super().__new__(cls, value)


class VentilationTimeRemaining(int):
    """Integer-compatible remaining ventilation timer value reported by the API."""

    def __new__(cls, value: int) -> Self:
        return super().__new__(cls, value)


class VentilationTimeEnd(int):
    """Integer-compatible ventilation timer end value reported by the API."""

    def __new__(cls, value: int) -> Self:
        return super().__new__(cls, value)


class VentilationFlowLevelTarget(int):
    """Integer-compatible ventilation flow target value reported by the API."""

    def __new__(cls, value: int) -> Self:
        return super().__new__(cls, value)


class NodeCo2Ppm(int):
    """Integer-compatible CO2 reading reported by node sensors."""

    def __new__(cls, value: int) -> Self:
        return super().__new__(cls, value)


class NodeAirQualityIndex(int):
    """Integer-compatible node air-quality score reported by the API."""

    def __new__(cls, value: int) -> Self:
        return super().__new__(cls, value)


class NodeRelativeHumidity(float):
    """Float-compatible relative humidity reading reported by node sensors."""

    def __new__(cls, value: float) -> Self:
        return super().__new__(cls, value)


class NodeTemperature(float):
    """Float-compatible temperature reading reported by node sensors."""

    def __new__(cls, value: float) -> Self:
        return super().__new__(cls, value)


class NodeMotorDeviceType(int):
    """Integer-compatible node motor device type reported by the API."""

    def __new__(cls, value: int) -> Self:
        return super().__new__(cls, value)


class NodeMotorRequest(int):
    """Integer-compatible node motor request value reported by the API."""

    def __new__(cls, value: int) -> Self:
        return super().__new__(cls, value)


class NodeMotorPosition(int):
    """Integer-compatible node motor position value reported by the API."""

    def __new__(cls, value: int) -> Self:
        return super().__new__(cls, value)


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


def _coerce_node_type(value: NodeType | str) -> NodeType:
    """Normalize public node type values to `NodeType`."""
    if isinstance(value, NodeType):
        return value
    try:
        return NodeType(value)
    except ValueError:
        _LOGGER.debug(
            "Unknown node type %r received through public model construction; "
            "falling back to UNKNOWN",
            value,
        )
        return NodeType.UNKNOWN


def _coerce_network_type(value: NetworkType | str) -> NetworkType:
    """Normalize public network type values to `NetworkType`."""
    if isinstance(value, NetworkType):
        return value
    try:
        return NetworkType(value)
    except ValueError:
        _LOGGER.debug(
            "Unknown network type %r received through public model construction; "
            "falling back to UNKNOWN",
            value,
        )
        return NetworkType.UNKNOWN


def _coerce_node_subtype(value: NodeSubtype | int) -> NodeSubtype:
    """Normalize public node subtype values to `NodeSubtype`."""
    if isinstance(value, NodeSubtype):
        return value
    return NodeSubtype(value)


def _coerce_node_parent_id(value: NodeParentId | int) -> NodeParentId:
    """Normalize public node parent values to `NodeParentId`."""
    if isinstance(value, NodeParentId):
        return value
    return NodeParentId(value)


def _coerce_node_association_id(value: NodeAssociationId | int) -> NodeAssociationId:
    """Normalize public node association values to `NodeAssociationId`."""
    if isinstance(value, NodeAssociationId):
        return value
    return NodeAssociationId(value)


def _coerce_node_name(value: NodeName | str) -> NodeName:
    """Normalize public node name values to `NodeName`."""
    if isinstance(value, NodeName):
        return value
    return NodeName(value)


def _coerce_node_identify(value: NodeIdentify | int) -> NodeIdentify:
    """Normalize public node identify values to `NodeIdentify`."""
    if isinstance(value, NodeIdentify):
        return value
    return NodeIdentify(value)


def _coerce_ventilation_state(value: VentilationState | str) -> VentilationState:
    """Normalize public ventilation state values to `VentilationState`."""
    if isinstance(value, VentilationState):
        return value
    try:
        return VentilationState(value)
    except ValueError:
        _LOGGER.debug(
            "Unknown ventilation state %r received through public model construction; "
            "falling back to UNKNOWN",
            value,
        )
        return VentilationState.UNKNOWN


def _coerce_ventilation_mode(value: VentilationMode | str) -> VentilationMode:
    """Normalize public ventilation mode values to `VentilationMode`."""
    if isinstance(value, VentilationMode):
        return value
    try:
        return VentilationMode(value)
    except ValueError:
        _LOGGER.debug(
            "Unknown ventilation mode %r received through public model construction; "
            "falling back to UNKNOWN",
            value,
        )
        return VentilationMode.UNKNOWN


def _coerce_ventilation_time_remaining(
    value: VentilationTimeRemaining | int,
) -> VentilationTimeRemaining:
    """Normalize public ventilation remaining-time values."""
    if isinstance(value, VentilationTimeRemaining):
        return value
    return VentilationTimeRemaining(value)


def _coerce_ventilation_time_end(value: VentilationTimeEnd | int) -> VentilationTimeEnd:
    """Normalize public ventilation end-time values."""
    if isinstance(value, VentilationTimeEnd):
        return value
    return VentilationTimeEnd(value)


def _coerce_ventilation_flow_level_target(
    value: VentilationFlowLevelTarget | int,
) -> VentilationFlowLevelTarget:
    """Normalize public ventilation flow target values."""
    if isinstance(value, VentilationFlowLevelTarget):
        return value
    return VentilationFlowLevelTarget(value)


def _coerce_node_co2_ppm(value: NodeCo2Ppm | int) -> NodeCo2Ppm:
    """Normalize public CO2 sensor values to `NodeCo2Ppm`."""
    if isinstance(value, NodeCo2Ppm):
        return value
    return NodeCo2Ppm(value)


def _coerce_node_air_quality_index(
    value: NodeAirQualityIndex | int,
) -> NodeAirQualityIndex:
    """Normalize public air-quality values to `NodeAirQualityIndex`."""
    if isinstance(value, NodeAirQualityIndex):
        return value
    return NodeAirQualityIndex(value)


def _coerce_node_relative_humidity(
    value: NodeRelativeHumidity | float,
) -> NodeRelativeHumidity:
    """Normalize public humidity values to `NodeRelativeHumidity`."""
    if isinstance(value, NodeRelativeHumidity):
        return value
    return NodeRelativeHumidity(value)


def _coerce_node_temperature(value: NodeTemperature | float) -> NodeTemperature:
    """Normalize public temperature values to `NodeTemperature`."""
    if isinstance(value, NodeTemperature):
        return value
    return NodeTemperature(value)


def _coerce_node_motor_device_type(
    value: NodeMotorDeviceType | int,
) -> NodeMotorDeviceType:
    """Normalize public motor device type values."""
    if isinstance(value, NodeMotorDeviceType):
        return value
    return NodeMotorDeviceType(value)


def _coerce_node_motor_request(value: NodeMotorRequest | int) -> NodeMotorRequest:
    """Normalize public motor request values to `NodeMotorRequest`."""
    if isinstance(value, NodeMotorRequest):
        return value
    return NodeMotorRequest(value)


def _coerce_node_motor_position(value: NodeMotorPosition | int) -> NodeMotorPosition:
    """Normalize public motor position values to `NodeMotorPosition`."""
    if isinstance(value, NodeMotorPosition):
        return value
    return NodeMotorPosition(value)


class DiagStatus(StrEnum):
    """Known normalized health states returned by the diagnostics API."""

    OK = "ok"
    DISABLED = "disabled"
    ERROR = "error"

    @classmethod
    def from_api_value(cls, value: str) -> Self | None:
        """Return the known normalized status for a raw API value."""
        return {
            "Ok": cls.OK,
            "Disable": cls.DISABLED,
            "Error": cls.ERROR,
        }.get(value)


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


class KnownActionName(StrEnum):
    """Observed stable action names published by the Duco public API notes."""

    SET_TIME = "SetTime"
    SET_IDENTIFY = "SetIdentify"
    SET_IDENTIFY_ALL = "SetIdentifyAll"
    RECONNECT_WIFI = "ReconnectWifi"
    SCAN_WIFI = "ScanWifi"
    SET_WIFI_AP_MODE = "SetWifiApMode"
    SET_VENTILATION_STATE = "SetVentilationState"
    SET_POS_MAN = "SetPosMan"
    SET_POS_MAN_CNT = "SetPosManCnt"


class ActionName(str):
    """String-compatible action name with optional known-value matching."""

    def __new__(cls, value: str) -> Self:
        return super().__new__(cls, value)

    @property
    def known_value(self) -> KnownActionName | None:
        """Return the matched known action name when available."""
        try:
            return KnownActionName(self)
        except ValueError:
            return None

    @property
    def is_known(self) -> bool:
        """Return whether the action name matches a documented stable value."""
        return self.known_value is not None


class ActionEnumValue(str):
    """String-compatible enum-backed option advertised for an action value."""

    def __new__(cls, value: str) -> Self:
        return super().__new__(cls, value)


def _coerce_action_name(value: ActionName | str) -> ActionName:
    """Normalize public action name values to `ActionName`."""
    if isinstance(value, ActionName):
        return value
    return ActionName(value)


def _coerce_action_enum_value(value: ActionEnumValue | str) -> ActionEnumValue:
    """Normalize discovered action enum options to `ActionEnumValue`."""
    if isinstance(value, ActionEnumValue):
        return value
    return ActionEnumValue(value)


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
class VentilationTemperatureInfo:
    """Ventilation temperature values reported by `/info?module=Ventilation`."""

    temp_oda: float | None = None
    temp_sup: float | None = None
    temp_eta: float | None = None
    temp_eha: float | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class BypassSupplyTemperatureTarget:
    """Bypass supply temperature target values exposed through `/config`."""

    zone_id: int
    value: float
    minimum: float | None = None
    increment: float | None = None
    maximum: float | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


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
class ConfigTime:
    """Stable time-related config fields returned by `/config`."""

    time_zone: ConfigValue | None = None
    dst: ConfigValue | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class ConfigModbus:
    """Stable Modbus config fields returned by `/config`."""

    addr: ConfigValue | None = None
    offset: ConfigValue | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class ConfigLan:
    """Stable LAN config fields returned by `/config`."""

    mode: ConfigValue | None = None
    dhcp: ConfigValue | None = None
    static_ip: ConfigValueString | None = None
    static_net_mask: ConfigValueString | None = None
    static_default_gateway: ConfigValueString | None = None
    static_dns: ConfigValueString | None = None
    wifi_client_ssid: ConfigValueString | None = None
    wifi_client_key: ConfigValueString | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class ConfigAutoRebootComm:
    """Stable communication reboot config fields returned by `/config`."""

    period: ConfigValue | None = None
    time: ConfigValue | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class ConfigGeneral:
    """Stable `General` config fields returned by `/config`."""

    time: ConfigTime | None = None
    modbus: ConfigModbus | None = None
    lan: ConfigLan | None = None
    auto_reboot_comm: ConfigAutoRebootComm | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class ConfigHeatRecoveryBypass:
    """Stable bypass config fields returned by `/config`."""

    temp_sup_tgt_zone_1: ConfigValue | None = None
    temp_sup_tgt_zone_2: ConfigValue | None = None
    temp_sup_tgt_zone_3: ConfigValue | None = None
    temp_sup_tgt_zone_4: ConfigValue | None = None
    temp_sup_tgt_zone_5: ConfigValue | None = None
    temp_sup_tgt_zone_6: ConfigValue | None = None
    temp_sup_tgt_zone_7: ConfigValue | None = None
    temp_sup_tgt_zone_8: ConfigValue | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class ConfigHeatRecovery:
    """Stable `HeatRecovery` config fields returned by `/config`."""

    bypass: ConfigHeatRecoveryBypass | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class Config:
    """Top-level config payload returned by the local Duco API."""

    sections: dict[str, ConfigSection] = field(default_factory=dict)
    general: ConfigGeneral | None = None
    heat_recovery: ConfigHeatRecovery | None = None
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
class ConfigZoneWithGroupStruct:
    """Readable zone config fields that include nested group entries."""

    name: ConfigValueString | None = None
    groups: list[ConfigGroup] = field(default_factory=list)
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


class _PatchPayloadModel:
    """Internal marker base class for typed patch payload models."""

    __slots__ = ()


class PatchConfigModel(_PatchPayloadModel):
    """Base class for typed `/config` patch payload models."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class PatchConfigValue:
    """Leaf config payload used by generic config write methods."""

    value: int | str


@dataclass(frozen=True, slots=True)
class PatchConfigTime(PatchConfigModel):
    """Typed time-related patch payload for `/config`."""

    time_zone: PatchConfigValue | None = field(
        default=None,
        metadata={"api_name": "TimeZone"},
    )
    dst: PatchConfigValue | None = field(default=None, metadata={"api_name": "Dst"})


@dataclass(frozen=True, slots=True)
class PatchConfigModbus(PatchConfigModel):
    """Typed Modbus patch payload for `/config`."""

    addr: PatchConfigValue | None = field(default=None, metadata={"api_name": "Addr"})
    offset: PatchConfigValue | None = field(default=None, metadata={"api_name": "Offset"})


@dataclass(frozen=True, slots=True)
class PatchConfigLan(PatchConfigModel):
    """Typed LAN patch payload for `/config`."""

    mode: PatchConfigValue | None = field(default=None, metadata={"api_name": "Mode"})
    dhcp: PatchConfigValue | None = field(default=None, metadata={"api_name": "Dhcp"})
    static_ip: PatchConfigValue | None = field(default=None, metadata={"api_name": "StaticIp"})
    static_net_mask: PatchConfigValue | None = field(
        default=None,
        metadata={"api_name": "StaticNetMask"},
    )
    static_default_gateway: PatchConfigValue | None = field(
        default=None,
        metadata={"api_name": "StaticDefaultGateway"},
    )
    static_dns: PatchConfigValue | None = field(default=None, metadata={"api_name": "StaticDns"})
    wifi_client_ssid: PatchConfigValue | None = field(
        default=None,
        metadata={"api_name": "WifiClientSsid"},
    )
    wifi_client_key: PatchConfigValue | None = field(
        default=None,
        metadata={"api_name": "WifiClientKey"},
    )


@dataclass(frozen=True, slots=True)
class PatchConfigAutoRebootComm(PatchConfigModel):
    """Typed auto-reboot communication patch payload for `/config`."""

    period: PatchConfigValue | None = field(default=None, metadata={"api_name": "Period"})
    time: PatchConfigValue | None = field(default=None, metadata={"api_name": "Time"})


@dataclass(frozen=True, slots=True)
class PatchConfigGeneral(PatchConfigModel):
    """Typed `General` patch payload for `/config`."""

    time: PatchConfigTime | None = field(default=None, metadata={"api_name": "Time"})
    modbus: PatchConfigModbus | None = field(default=None, metadata={"api_name": "Modbus"})
    lan: PatchConfigLan | None = field(default=None, metadata={"api_name": "Lan"})
    auto_reboot_comm: PatchConfigAutoRebootComm | None = field(
        default=None,
        metadata={"api_name": "AutoRebootComm"},
    )


@dataclass(frozen=True, slots=True)
class PatchConfigHeatRecoveryBypass(PatchConfigModel):
    """Typed bypass patch payload for `/config`."""

    temp_sup_tgt_zone_1: PatchConfigValue | None = field(
        default=None,
        metadata={"api_name": "TempSupTgtZone1"},
    )
    temp_sup_tgt_zone_2: PatchConfigValue | None = field(
        default=None,
        metadata={"api_name": "TempSupTgtZone2"},
    )
    temp_sup_tgt_zone_3: PatchConfigValue | None = field(
        default=None,
        metadata={"api_name": "TempSupTgtZone3"},
    )
    temp_sup_tgt_zone_4: PatchConfigValue | None = field(
        default=None,
        metadata={"api_name": "TempSupTgtZone4"},
    )
    temp_sup_tgt_zone_5: PatchConfigValue | None = field(
        default=None,
        metadata={"api_name": "TempSupTgtZone5"},
    )
    temp_sup_tgt_zone_6: PatchConfigValue | None = field(
        default=None,
        metadata={"api_name": "TempSupTgtZone6"},
    )
    temp_sup_tgt_zone_7: PatchConfigValue | None = field(
        default=None,
        metadata={"api_name": "TempSupTgtZone7"},
    )
    temp_sup_tgt_zone_8: PatchConfigValue | None = field(
        default=None,
        metadata={"api_name": "TempSupTgtZone8"},
    )


@dataclass(frozen=True, slots=True)
class PatchConfigHeatRecovery(PatchConfigModel):
    """Typed `HeatRecovery` patch payload for `/config`."""

    bypass: PatchConfigHeatRecoveryBypass | None = field(
        default=None,
        metadata={"api_name": "Bypass"},
    )


@dataclass(frozen=True, slots=True)
class PatchConfig(PatchConfigModel):
    """Typed top-level patch payload for `/config`."""

    general: PatchConfigGeneral | None = field(default=None, metadata={"api_name": "General"})
    heat_recovery: PatchConfigHeatRecovery | None = field(
        default=None,
        metadata={"api_name": "HeatRecovery"},
    )


@dataclass(frozen=True, slots=True)
class PatchConfigZoneGeneral(_PatchPayloadModel):
    """Typed `General` patch payload under `DeviceGroupConfig` for a zone."""

    name: PatchConfigValue | None = field(default=None, metadata={"api_name": "Name"})


@dataclass(frozen=True, slots=True)
class PatchConfigZoneDeviceGroupConfig(_PatchPayloadModel):
    """Typed `DeviceGroupConfig` patch payload for `/config/zones/{zone}`."""

    general: PatchConfigZoneGeneral | None = field(
        default=None,
        metadata={"api_name": "General"},
    )


@dataclass(frozen=True, slots=True)
class PatchConfigZoneStruct(_PatchPayloadModel):
    """Typed zone config patch payload for stable writable zone fields."""

    device_group_config: PatchConfigZoneDeviceGroupConfig | None = field(
        default=None,
        metadata={"api_name": "DeviceGroupConfig"},
    )


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
class PatchConfigNodeStruct(_PatchPayloadModel):
    """Typed node config patch payload for stable writable node fields."""

    name: PatchConfigNodeValue | None = field(default=None, metadata={"api_name": "Name"})


@dataclass(frozen=True, slots=True, init=False)
class NodeSensorInfo:
    """Sensor readings reported for a node."""

    co2: NodeCo2Ppm | None = None
    iaq_co2: NodeAirQualityIndex | None = None
    rh: NodeRelativeHumidity | None = None
    iaq_rh: NodeAirQualityIndex | None = None
    temp: NodeTemperature | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def __init__(
        self,
        co2: NodeCo2Ppm | int | None = None,
        iaq_co2: NodeAirQualityIndex | int | None = None,
        rh: NodeRelativeHumidity | float | None = None,
        iaq_rh: NodeAirQualityIndex | int | None = None,
        temp: NodeTemperature | float | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> None:
        """Initialize node sensor info with compatibility-friendly constructor types."""
        object.__setattr__(self, "co2", None if co2 is None else _coerce_node_co2_ppm(co2))
        object.__setattr__(
            self,
            "iaq_co2",
            None if iaq_co2 is None else _coerce_node_air_quality_index(iaq_co2),
        )
        object.__setattr__(
            self,
            "rh",
            None if rh is None else _coerce_node_relative_humidity(rh),
        )
        object.__setattr__(
            self,
            "iaq_rh",
            None if iaq_rh is None else _coerce_node_air_quality_index(iaq_rh),
        )
        object.__setattr__(
            self,
            "temp",
            None if temp is None else _coerce_node_temperature(temp),
        )
        object.__setattr__(self, "raw_payload", {} if raw_payload is None else raw_payload)


@dataclass(frozen=True, slots=True, init=False)
class NodeMotorStateInfo:
    """Motor controller state reported for a node."""

    device_type: NodeMotorDeviceType | None = None
    req: NodeMotorRequest | None = None
    pos_req: NodeMotorPosition | None = None
    pos: NodeMotorPosition | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def __init__(
        self,
        device_type: NodeMotorDeviceType | int | None = None,
        req: NodeMotorRequest | int | None = None,
        pos_req: NodeMotorPosition | int | None = None,
        pos: NodeMotorPosition | int | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> None:
        """Initialize motor state info with compatibility-friendly constructor types."""
        object.__setattr__(
            self,
            "device_type",
            None if device_type is None else _coerce_node_motor_device_type(device_type),
        )
        object.__setattr__(
            self,
            "req",
            None if req is None else _coerce_node_motor_request(req),
        )
        object.__setattr__(
            self,
            "pos_req",
            None if pos_req is None else _coerce_node_motor_position(pos_req),
        )
        object.__setattr__(
            self,
            "pos",
            None if pos is None else _coerce_node_motor_position(pos),
        )
        object.__setattr__(self, "raw_payload", {} if raw_payload is None else raw_payload)


@dataclass(frozen=True, slots=True, init=False)
class NodeVentilationInfo:
    """Ventilation state and timers reported for a node."""

    state: VentilationState
    mode: VentilationMode
    time_state_remain: VentilationTimeRemaining
    time_state_end: VentilationTimeEnd
    flow_lvl_tgt: VentilationFlowLevelTarget | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def __init__(
        self,
        state: VentilationState | str,
        mode: VentilationMode | str,
        time_state_remain: VentilationTimeRemaining | int,
        time_state_end: VentilationTimeEnd | int,
        flow_lvl_tgt: VentilationFlowLevelTarget | int | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> None:
        """Initialize ventilation info with compatibility-friendly constructor types."""
        object.__setattr__(self, "state", _coerce_ventilation_state(state))
        object.__setattr__(self, "mode", _coerce_ventilation_mode(mode))
        object.__setattr__(
            self,
            "time_state_remain",
            _coerce_ventilation_time_remaining(time_state_remain),
        )
        object.__setattr__(
            self,
            "time_state_end",
            _coerce_ventilation_time_end(time_state_end),
        )
        object.__setattr__(
            self,
            "flow_lvl_tgt",
            None if flow_lvl_tgt is None else _coerce_ventilation_flow_level_target(flow_lvl_tgt),
        )
        object.__setattr__(self, "raw_payload", {} if raw_payload is None else raw_payload)


@dataclass(frozen=True, slots=True, init=False)
class NodeGeneralInfo:
    """Static node metadata used to identify a device."""

    node_type: NodeType
    sub_type: NodeSubtype
    network_type: NetworkType
    parent: NodeParentId
    asso: NodeAssociationId
    name: NodeName
    identify: NodeIdentify
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def __init__(
        self,
        node_type: NodeType | str,
        sub_type: NodeSubtype | int,
        network_type: NetworkType | str,
        parent: NodeParentId | int,
        asso: NodeAssociationId | int,
        name: NodeName | str,
        identify: NodeIdentify | int,
        raw_payload: dict[str, Any] | None = None,
    ) -> None:
        """Initialize node general info with compatibility-friendly constructor types."""
        object.__setattr__(self, "node_type", _coerce_node_type(node_type))
        object.__setattr__(self, "sub_type", _coerce_node_subtype(sub_type))
        object.__setattr__(self, "network_type", _coerce_network_type(network_type))
        object.__setattr__(self, "parent", _coerce_node_parent_id(parent))
        object.__setattr__(self, "asso", _coerce_node_association_id(asso))
        object.__setattr__(self, "name", _coerce_node_name(name))
        object.__setattr__(self, "identify", _coerce_node_identify(identify))
        object.__setattr__(self, "raw_payload", {} if raw_payload is None else raw_payload)


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


@dataclass(frozen=True, slots=True, init=False)
class DiagComponent:
    """Health state for a diagnostic subsystem."""

    component: str
    status: DiagStatus | None
    raw_status: str
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def __init__(
        self,
        component: str,
        status: DiagStatus | str | None,
        raw_status: str | dict[str, Any] | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a diagnostic subsystem with legacy argument compatibility."""
        if isinstance(raw_status, dict):
            if raw_payload is not None:
                raise TypeError("raw_payload was provided more than once")
            raw_payload = raw_status
            raw_status = None

        normalized_status: DiagStatus | None
        if isinstance(status, DiagStatus):
            normalized_status = status
        elif isinstance(status, str):
            normalized_status = DiagStatus.from_api_value(status)
        else:
            normalized_status = None
        if raw_status is None:
            if not isinstance(status, str) or isinstance(status, DiagStatus):
                raise TypeError("raw_status is required for typed diagnostic statuses")
            raw_status = status

        object.__setattr__(self, "component", component)
        object.__setattr__(self, "status", normalized_status)
        object.__setattr__(self, "raw_status", raw_status)
        object.__setattr__(self, "raw_payload", {} if raw_payload is None else raw_payload)


@dataclass(frozen=True, slots=True)
class DiagInfo:
    """Diagnostic subsystem payload returned by the local Duco API."""

    diagnostic_subsystems: tuple[DiagComponent, ...] = ()
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True, init=False)
class Action:
    """System action request payload."""

    action: ActionName
    val: str | int | bool | None = None

    def __init__(
        self,
        action: ActionName | str,
        val: str | int | bool | None = None,
    ) -> None:
        """Initialize a system action request with compatibility-friendly types."""
        object.__setattr__(self, "action", _coerce_action_name(action))
        object.__setattr__(self, "val", val)


@dataclass(frozen=True, slots=True, init=False)
class ActionNode:
    """Node action request payload."""

    action: ActionName
    val: str | int | bool | None = None

    def __init__(
        self,
        action: ActionName | str,
        val: str | int | bool | None = None,
    ) -> None:
        """Initialize a node action request with compatibility-friendly types."""
        object.__setattr__(self, "action", _coerce_action_name(action))
        object.__setattr__(self, "val", val)


@dataclass(frozen=True, slots=True, init=False)
class ActionItem:
    """Action definition returned by action discovery endpoints."""

    action: ActionName
    val_type: ActionValueType
    enum_values: list[ActionEnumValue] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def __init__(
        self,
        action: ActionName | str,
        val_type: ActionValueType,
        enum_values: list[ActionEnumValue | str] | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> None:
        """Initialize an action discovery item with compatibility-friendly types."""
        object.__setattr__(self, "action", _coerce_action_name(action))
        object.__setattr__(self, "val_type", val_type)
        object.__setattr__(
            self,
            "enum_values",
            []
            if enum_values is None
            else [_coerce_action_enum_value(value) for value in enum_values],
        )
        object.__setattr__(self, "raw_payload", {} if raw_payload is None else raw_payload)


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
