"""Typed models for values exposed by the local Duco API."""

from dataclasses import dataclass, field
from enum import StrEnum


class NodeType(StrEnum):
    """Node categories reported by the box."""

    BOX = "BOX"
    UCCO2 = "UCCO2"
    UCRH = "UCRH"
    UCBAT = "UCBAT"
    UC = "UC"
    BSRH = "BSRH"
    VLV = "VLV"
    UNKNOWN = "UNKNOWN"


class NetworkType(StrEnum):
    """Transport types reported for node connectivity."""

    VIRT = "VIRT"
    RF = "RF"
    WI = "WI"
    UNKNOWN = "UNKNOWN"


class VentilationMode(StrEnum):
    """Control modes reported for node ventilation, plus a client-side fallback."""

    AUTO = "AUTO"
    MANU = "MANU"
    NONE = "-"
    UNKNOWN = "UNKNOWN"


class VentilationState(StrEnum):
    """Ventilation states reported by the API, plus a client-side fallback."""

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


@dataclass(frozen=True, slots=True)
class ApiEndpoint:
    """Capabilities advertised for a single API endpoint."""

    url: str
    methods: list[str] = field(default_factory=list)
    query_parameters: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ApiInfo:
    """Version and endpoint metadata returned by the API root."""

    public_api_version: str
    reported_api_version: str | None = None
    endpoints: list[ApiEndpoint] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BoardInfo:
    """Identity and version fields for the main Duco unit."""

    box_name: str
    box_sub_type_name: str
    serial_board_box: str
    serial_board_comm: str
    serial_duco_box: str
    serial_duco_comm: str
    time: int
    public_api_version: str | None = None
    software_version: str | None = None


@dataclass(frozen=True, slots=True)
class LanInfo:
    """LAN settings reported by the main unit."""

    mode: str
    ip: str
    net_mask: str
    default_gateway: str
    dns: str
    mac: str
    host_name: str
    rssi_wifi: int | None


@dataclass(frozen=True, slots=True)
class NodeSensorInfo:
    """Sensor readings reported for a node."""

    co2: int | None = None
    iaq_co2: int | None = None
    rh: float | None = None
    iaq_rh: int | None = None
    temp: float | None = None


@dataclass(frozen=True, slots=True)
class NodeVentilationInfo:
    """Ventilation state and timers reported for a node."""

    state: VentilationState
    mode: VentilationMode
    time_state_remain: int
    time_state_end: int
    flow_lvl_tgt: int | None = None


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


@dataclass(frozen=True, slots=True)
class Node:
    """Node returned by the local Duco API."""

    node_id: int
    general: NodeGeneralInfo
    ventilation: NodeVentilationInfo | None = None
    sensor: NodeSensorInfo | None = None


@dataclass(frozen=True, slots=True)
class DiagComponent:
    """Health state for a diagnostic subsystem."""

    component: str
    status: DiagStatus
