"""Public package exports for python-duco-connectivity."""

from importlib.metadata import PackageNotFoundError, version

from .client import DucoClient
from .exceptions import (
    DucoConnectionError,
    DucoError,
    DucoRateLimitError,
    DucoWriteLimitError,
)
from .models import (
    ActionResult,
    ActionResultStatus,
    ApiEndpoint,
    ApiEndpointInfo,
    ApiInfo,
    BoardInfo,
    Config,
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
    PatchConfigNodeValue,
    PatchConfigValue,
    VentilationMode,
    VentilationState,
)

try:
    __version__ = version("python-duco-connectivity")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "ActionResult",
    "ActionResultStatus",
    "ApiEndpoint",
    "ApiEndpointInfo",
    "ApiInfo",
    "BoardInfo",
    "Config",
    "ConfigNode",
    "ConfigNodeOverview",
    "ConfigNodeStruct",
    "ConfigSection",
    "ConfigValue",
    "ConfigValueOptions",
    "ConfigValueString",
    "DucoClient",
    "DucoConnectionError",
    "DucoError",
    "DucoRateLimitError",
    "DucoWriteLimitError",
    "DiagComponent",
    "DiagStatus",
    "LanInfo",
    "NetworkType",
    "Node",
    "NodeGeneralInfo",
    "NodeOverview",
    "NodeSensorInfo",
    "NodeType",
    "NodeVentilationInfo",
    "PatchConfigNodeValue",
    "PatchConfigValue",
    "VentilationMode",
    "VentilationState",
    "__version__",
]
