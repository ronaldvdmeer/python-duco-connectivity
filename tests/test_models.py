"""Tests for the public data models."""

import pytest

from duco_connectivity import (
    ApiEndpoint,
    ApiInfo,
    BoardInfo,
    NetworkType,
    Node,
    NodeGeneralInfo,
    NodeSensorInfo,
    NodeType,
    NodeVentilationInfo,
    VentilationMode,
    VentilationState,
)


def test_api_endpoint_defaults() -> None:
    """ApiEndpoint should default to empty metadata lists."""
    endpoint = ApiEndpoint(url="/api")
    assert endpoint.methods == []
    assert endpoint.query_parameters == []
    assert endpoint.modules == []


def test_api_info_defaults() -> None:
    """ApiInfo should allow omitted optional fields."""
    info = ApiInfo(public_api_version="2.5")
    assert info.public_api_version == "2.5"
    assert info.reported_api_version is None
    assert info.endpoints == []


def test_board_info_optional_software_version() -> None:
    """BoardInfo should keep software_version optional."""
    board = BoardInfo(
        box_name="SILENT_CONNECT",
        box_sub_type_name="Eu",
        serial_board_box="RS0000000001",
        serial_board_comm="PS0000000001",
        serial_duco_box="n/a",
        serial_duco_comm="P000000-000000-001",
        time=1775082497,
    )
    assert board.software_version is None


def test_node_sensor_info_defaults() -> None:
    """NodeSensorInfo should default all optional fields to None."""
    sensor = NodeSensorInfo()
    assert sensor.co2 is None
    assert sensor.iaq_co2 is None
    assert sensor.rh is None
    assert sensor.iaq_rh is None
    assert sensor.temp is None


def test_node_ventilation_info_flow_target_is_optional() -> None:
    """NodeVentilationInfo should allow omitted flow target."""
    ventilation = NodeVentilationInfo(
        state=VentilationState.CNT1,
        time_state_remain=0,
        time_state_end=0,
        mode=VentilationMode.NONE,
    )
    assert ventilation.flow_lvl_tgt is None


def test_node_is_frozen() -> None:
    """The public node model should remain immutable."""
    node = Node(
        node_id=1,
        general=NodeGeneralInfo(
            node_type=NodeType.BOX,
            sub_type=1,
            network_type=NetworkType.VIRT,
            parent=0,
            asso=0,
            name="",
            identify=0,
        ),
    )
    with pytest.raises(AttributeError):
        node.node_id = 2  # type: ignore[misc]
