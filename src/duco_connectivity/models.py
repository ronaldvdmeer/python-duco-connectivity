"""Typed models for values exposed by the local Duco API."""

import logging
import sys
from dataclasses import dataclass, field
from enum import StrEnum
from types import FrameType

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
    MB = "MB"
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


@dataclass(frozen=True, slots=True, init=False)
class ApiInfo:
    """Version and endpoint metadata returned by the API root."""

    public_api_version: str
    reported_api_version: str | None = None
    endpoints: list[ApiEndpoint] = field(default_factory=list)

    def __init__(
        self,
        public_api_version: str | None = None,
        reported_api_version: str | None = None,
        endpoints: list[ApiEndpoint] | None = None,
        *,
        api_version: str | None = None,
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

        object.__setattr__(self, "public_api_version", resolved_public_api_version)
        object.__setattr__(self, "reported_api_version", reported_api_version)
        object.__setattr__(self, "endpoints", [] if endpoints is None else endpoints)

    @property
    def api_version(self) -> str:
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
