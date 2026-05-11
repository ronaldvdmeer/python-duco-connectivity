"""Tests for the public data models."""

import logging

import pytest

from duco_connectivity import (
    Action,
    ActionItem,
    ActionNode,
    ActionValueType,
    ApiEndpoint,
    ApiEndpointInfo,
    ApiInfo,
    BoardInfo,
    NetworkType,
    Node,
    NodeActionItemList,
    NodeGeneralInfo,
    NodeListActionItemList,
    NodeSensorInfo,
    NodeType,
    NodeVentilationInfo,
    VentilationMode,
    VentilationState,
)


def _build_wrapper(module_name: str, source: str) -> object:
    """Create a wrapper function in a custom module namespace."""
    namespace = {"__name__": module_name}
    exec(source, namespace)
    return namespace["external_wrapper"]


def test_api_endpoint_defaults() -> None:
    """ApiEndpoint should default to empty metadata lists."""
    endpoint = ApiEndpoint(url="/api")
    assert endpoint.methods == []
    assert endpoint.query_parameters == []
    assert endpoint.modules == []


def test_action_defaults() -> None:
    """Action should allow omitted optional values."""
    action = Action(action="SetTime")
    assert action.action == "SetTime"
    assert action.val is None


def test_action_node_defaults() -> None:
    """ActionNode should allow omitted optional values."""
    action = ActionNode(action="SetIdentify")
    assert action.action == "SetIdentify"
    assert action.val is None


def test_action_item_defaults() -> None:
    """ActionItem should default enum values to an empty list."""
    item = ActionItem(action="SetIdentify", val_type=ActionValueType.NONE)
    assert item.action == "SetIdentify"
    assert item.val_type is ActionValueType.NONE
    assert item.enum_values == []


def test_node_action_item_list_defaults() -> None:
    """NodeActionItemList should default actions to an empty list."""
    item_list = NodeActionItemList(node=1)
    assert item_list.node == 1
    assert item_list.actions == []


def test_node_list_action_item_list_defaults() -> None:
    """NodeListActionItemList should default nodes to an empty list."""
    item_list = NodeListActionItemList()
    assert item_list.nodes == []


def test_action_value_type_values() -> None:
    """ActionValueType should expose the API-defined discovery values."""
    assert ActionValueType.NONE.value == "None"
    assert ActionValueType.BOOLEAN.value == "Boolean"
    assert ActionValueType.INTEGER.value == "Integer"
    assert ActionValueType.STRING.value == "String"
    assert ActionValueType.ENUM.value == "Enum"
    assert ActionValueType.UNKNOWN.value == "UNKNOWN"


def test_api_info_defaults() -> None:
    """ApiInfo should allow omitted optional fields."""
    info = ApiInfo(public_api_version="2.5")
    assert info.public_api_version == "2.5"
    assert info.api_version == "2.5"
    assert info.reported_api_version is None
    assert info.endpoints == []


def test_api_info_accepts_legacy_api_version_argument() -> None:
    """ApiInfo should accept the old api_version keyword."""
    info = ApiInfo(api_version="2.5")
    assert info.public_api_version == "2.5"
    assert info.api_version == "2.5"


def test_api_info_accepts_previous_positional_signature() -> None:
    """ApiInfo should still accept the old positional optional fields."""
    endpoint = ApiEndpoint(url="/api")

    info = ApiInfo("2.5", "reported", [endpoint])

    assert info.public_api_version == "2.5"
    assert info.reported_api_version == "reported"
    assert info.endpoints == [endpoint]


def test_api_info_accepts_positional_optional_fields_with_legacy_keyword() -> None:
    """Legacy api_version support should not block the old positional optional fields."""
    endpoint = ApiEndpoint(url="/api")

    info = ApiInfo(None, "reported", [endpoint], api_version="2.5")

    assert info.public_api_version == "2.5"
    assert info.reported_api_version == "reported"
    assert info.endpoints == [endpoint]


def test_api_info_legacy_api_version_argument_logs_external_caller(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Using the old constructor keyword should log the external caller."""

    def external_wrapper() -> ApiInfo:
        return ApiInfo(api_version="2.5")

    with caplog.at_level(logging.DEBUG, logger="duco_connectivity.models"):
        info = external_wrapper()

    assert info.public_api_version == "2.5"
    assert (
        "Compatibility constructor argument api_version used by "
        "test_models.external_wrapper; mapping to public_api_version."
    ) in caplog.text


def test_api_info_legacy_api_version_property_logs_external_caller(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Using the old property should log the external caller."""
    info = ApiInfo(public_api_version="2.5")

    def external_wrapper() -> str:
        return info.api_version

    with caplog.at_level(logging.DEBUG, logger="duco_connectivity.models"):
        value = external_wrapper()

    assert value == "2.5"
    assert (
        "Compatibility property api_version accessed by "
        "test_models.external_wrapper; delegating to public_api_version."
    ) in caplog.text


def test_api_info_legacy_api_version_property_treats_prefixed_external_module_as_external(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Modules like duco_connectivity_tools should not be treated as internal."""
    info = ApiInfo(public_api_version="2.5")
    external_wrapper = _build_wrapper(
        "duco_connectivity_tools",
        "def external_wrapper(info):\n    return info.api_version\n",
    )

    with caplog.at_level(logging.DEBUG, logger="duco_connectivity.models"):
        value = external_wrapper(info)

    assert value == "2.5"
    assert (
        "Compatibility property api_version accessed by "
        "duco_connectivity_tools.external_wrapper; delegating to public_api_version."
    ) in caplog.text


def test_api_endpoint_info_alias_points_to_api_endpoint() -> None:
    """ApiEndpointInfo should remain import-compatible with ApiEndpoint."""
    assert ApiEndpointInfo is ApiEndpoint


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


def test_network_type_includes_mb() -> None:
    """NetworkType should expose MB as an explicit known value."""
    assert NetworkType.MB.value == "MB"
