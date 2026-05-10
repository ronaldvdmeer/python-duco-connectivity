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
    ApiEndpoint,
    ApiEndpointInfo,
    ApiInfo,
    BoardInfo,
    Config,
    ConfigSection,
    ConfigValue,
    ConfigValueString,
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

try:
    __version__ = version("python-duco-connectivity")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "ApiEndpoint",
    "ApiEndpointInfo",
    "ApiInfo",
    "BoardInfo",
    "Config",
    "ConfigSection",
    "ConfigValue",
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
    "NodeSensorInfo",
    "NodeType",
    "NodeVentilationInfo",
    "VentilationMode",
    "VentilationState",
    "__version__",
]
