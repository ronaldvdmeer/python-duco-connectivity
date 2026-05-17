"""Tests for the public data models."""

import inspect
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
    BoardName,
    ConfigGeneralSubmoduleSelector,
    ConfigGroup,
    ConfigGroupStruct,
    ConfigHeatRecoverySubmoduleSelector,
    ConfigModuleSelector,
    ConfigValueString,
    ConfigZone,
    ConfigZonesOverview,
    ConfigZoneStruct,
    DeviceGroupConfigSubmoduleSelector,
    DucoSerialNumber,
    DucoVersion,
    HostName,
    InfoGeneralSubmoduleSelector,
    InfoGroup,
    InfoGroupStruct,
    InfoModuleSelector,
    InfoZone,
    InfoZoneGroup,
    InfoZonesOverview,
    InfoZoneStruct,
    IpAddress,
    KnownBoardName,
    KnownLanMode,
    LanInfo,
    LanMode,
    MacAddress,
    NetworkType,
    Node,
    NodeActionItemList,
    NodeAirQualityIndex,
    NodeAssociationId,
    NodeCo2Ppm,
    NodeGeneralInfo,
    NodeIdentify,
    NodeInfoModuleSelector,
    NodeListActionItemList,
    NodeMotorDeviceType,
    NodeMotorPosition,
    NodeMotorRequest,
    NodeMotorStateInfo,
    NodeName,
    NodeParentId,
    NodeRelativeHumidity,
    NodeSensorInfo,
    NodeSubtype,
    NodeTemperature,
    NodeType,
    NodeVentilationInfo,
    VentilationFlowLevelTarget,
    VentilationMode,
    VentilationState,
    VentilationTimeEnd,
    VentilationTimeRemaining,
    ZoneModuleSelector,
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
    assert endpoint.raw_payload == {}


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
    assert item.raw_payload == {}


def test_node_action_item_list_defaults() -> None:
    """NodeActionItemList should default actions to an empty list."""
    item_list = NodeActionItemList(node_id=1)
    assert item_list.node_id == 1
    assert item_list.actions == []
    assert item_list.raw_payload == {}


def test_node_list_action_item_list_defaults() -> None:
    """NodeListActionItemList should default nodes to an empty list."""
    item_list = NodeListActionItemList()
    assert item_list.nodes == []
    assert item_list.raw_payload == {}


def test_action_value_type_values() -> None:
    """ActionValueType should expose the API-defined discovery values."""
    assert ActionValueType.NONE.value == "None"
    assert ActionValueType.BOOLEAN.value == "Boolean"
    assert ActionValueType.INTEGER.value == "Integer"
    assert ActionValueType.STRING.value == "String"
    assert ActionValueType.ENUM.value == "Enum"
    assert ActionValueType.UNKNOWN.value == "UNKNOWN"


def test_ventilation_mode_values() -> None:
    """VentilationMode should expose the documented public API values explicitly."""
    assert {mode.value for mode in VentilationMode} == {
        "-",
        "AUTO",
        "MANU",
        "OVRL",
        "EXTN",
        "COOL",
        "N/A",
        "DSBL",
        "UNKNOWN",
    }
    assert VentilationMode.NONE.value == "-"
    assert VentilationMode.NA.value == "N/A"


def test_ventilation_state_values() -> None:
    """VentilationState should expose documented and compatibility members explicitly."""
    assert {state.value for state in VentilationState} == {
        "AUTO",
        "AUT1",
        "AUT2",
        "AUT3",
        "MAN1",
        "MAN2",
        "MAN3",
        "EMPT",
        "CNT1",
        "CNT2",
        "CNT3",
        "-",
        "MAN1x2",
        "MAN2x2",
        "MAN3x2",
        "MAN1x3",
        "MAN2x3",
        "MAN3x3",
        "UNKNOWN",
    }
    assert VentilationState.NONE.value == "-"
    assert VentilationState.MAN3x2.value == "MAN3x2"


def test_selector_enum_values() -> None:
    """Known selector enums should expose the documented stable selector values."""
    assert InfoModuleSelector.GENERAL.value == "General"
    assert InfoGeneralSubmoduleSelector.PUBLIC_API.value == "PublicApi"
    assert ConfigModuleSelector.HEAT_RECOVERY.value == "HeatRecovery"
    assert ConfigGeneralSubmoduleSelector.AUTO_REBOOT_COMM.value == "AutoRebootComm"
    assert ConfigHeatRecoverySubmoduleSelector.BYPASS.value == "Bypass"
    assert NodeInfoModuleSelector.MOTOR_STATE_CTRL.value == "MotorStateCtrl"
    assert ZoneModuleSelector.DEVICE_GROUP_CONFIG.value == "DeviceGroupConfig"
    assert DeviceGroupConfigSubmoduleSelector.GENERAL.value == "General"


def test_board_name_known_value() -> None:
    """BoardName should expose observed stable board identities."""
    board_name = BoardName("SILENT_CONNECT")

    assert board_name == "SILENT_CONNECT"
    assert board_name.known_value is KnownBoardName.SILENT_CONNECT
    assert board_name.is_known is True


def test_board_name_unknown_value_is_forward_tolerant() -> None:
    """BoardName should preserve unknown identities without coercing them away."""
    board_name = BoardName("FUTURE_BOX")

    assert board_name == "FUTURE_BOX"
    assert board_name.known_value is None
    assert board_name.is_known is False


def test_duco_version_parses_numeric_components() -> None:
    """DucoVersion should expose parsed numeric version components."""
    version = DucoVersion("2.0.6.0")

    assert version == "2.0.6.0"
    assert version.components == (2, 0, 6, 0)
    assert version.major == 2
    assert version.minor == 0
    assert version.is_well_formed is True


def test_duco_version_preserves_malformed_values() -> None:
    """DucoVersion should keep malformed values string-compatible."""
    version = DucoVersion("2.beta")

    assert version == "2.beta"
    assert version.components is None
    assert version.major is None
    assert version.minor is None
    assert version.is_well_formed is False


def test_api_info_defaults() -> None:
    """ApiInfo should allow omitted optional fields."""
    info = ApiInfo(public_api_version="2.5")
    assert isinstance(info.public_api_version, DucoVersion)
    assert info.public_api_version == "2.5"
    assert info.public_api_version.components == (2, 5)
    assert info.api_version == "2.5"
    assert info.reported_api_version is None
    assert info.endpoints == []
    assert info.raw_payload == {}


def test_api_info_accepts_legacy_api_version_argument() -> None:
    """ApiInfo should accept the old api_version keyword."""
    info = ApiInfo(api_version="2.5")
    assert isinstance(info.public_api_version, DucoVersion)
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
    assert isinstance(board.box_name, BoardName)
    assert board.box_name.known_value is KnownBoardName.SILENT_CONNECT
    assert isinstance(board.serial_board_box, DucoSerialNumber)
    assert isinstance(board.serial_board_comm, DucoSerialNumber)
    assert isinstance(board.serial_duco_box, DucoSerialNumber)
    assert isinstance(board.serial_duco_comm, DucoSerialNumber)
    assert board.public_api_version is None
    assert board.software_version is None
    assert board.raw_payload == {}


def test_board_info_preserves_unknown_board_and_malformed_versions() -> None:
    """BoardInfo should keep unknown board names and malformed versions accessible."""
    board = BoardInfo(
        box_name="FUTURE_BOX",
        box_sub_type_name="Prototype",
        serial_board_box="RS0000000002",
        serial_board_comm="PS0000000002",
        serial_duco_box="P000000-000000-002",
        serial_duco_comm="P000000-000000-003",
        time=1775082498,
        public_api_version="2.beta",
        software_version="mainline",
    )

    assert isinstance(board.box_name, BoardName)
    assert board.box_name == "FUTURE_BOX"
    assert board.box_name.known_value is None
    assert isinstance(board.public_api_version, DucoVersion)
    assert board.public_api_version == "2.beta"
    assert board.public_api_version.components is None
    assert isinstance(board.software_version, DucoVersion)
    assert board.software_version == "mainline"
    assert board.software_version.components is None


def test_board_info_constructor_signature_accepts_compatibility_types() -> None:
    """BoardInfo should advertise compatibility-friendly constructor annotations."""
    signature = inspect.signature(BoardInfo)

    assert signature.parameters["box_name"].annotation == BoardName | str
    assert signature.parameters["serial_board_box"].annotation == DucoSerialNumber | str
    assert signature.parameters["serial_board_comm"].annotation == DucoSerialNumber | str
    assert signature.parameters["serial_duco_box"].annotation == DucoSerialNumber | str
    assert signature.parameters["serial_duco_comm"].annotation == DucoSerialNumber | str
    assert signature.parameters["public_api_version"].annotation == DucoVersion | str | None
    assert signature.parameters["software_version"].annotation == DucoVersion | str | None


def test_lan_info_coerces_string_metadata_primitives() -> None:
    """LanInfo should coerce exposed metadata into string-compatible typed wrappers."""
    lan = LanInfo(
        mode="WIFI_CLIENT",
        ip="192.0.2.94",
        net_mask="255.255.255.0",
        default_gateway="192.0.2.1",
        dns="192.0.2.1",
        mac="a0:dd:6c:06:12:90",
        host_name="duco_test_box",
        rssi_wifi=-44,
    )

    assert isinstance(lan.mode, LanMode)
    assert lan.mode.known_value is KnownLanMode.WIFI_CLIENT
    assert isinstance(lan.ip, IpAddress)
    assert isinstance(lan.net_mask, IpAddress)
    assert isinstance(lan.default_gateway, IpAddress)
    assert isinstance(lan.dns, IpAddress)
    assert isinstance(lan.mac, MacAddress)
    assert isinstance(lan.host_name, HostName)
    assert lan.raw_payload == {}


def test_lan_info_preserves_unknown_mode_and_unusual_metadata_strings() -> None:
    """LanInfo should keep forward-looking string values accessible."""
    lan = LanInfo(
        mode="FUTURE_WIFI",
        ip="not-an-ip",
        net_mask="maskish",
        default_gateway="gatewayish",
        dns="dnsish",
        mac="macish",
        host_name="future host",
        rssi_wifi=None,
    )

    assert isinstance(lan.mode, LanMode)
    assert lan.mode == "FUTURE_WIFI"
    assert lan.mode.known_value is None
    assert isinstance(lan.ip, IpAddress)
    assert lan.ip == "not-an-ip"
    assert isinstance(lan.mac, MacAddress)
    assert lan.mac == "macish"
    assert isinstance(lan.host_name, HostName)
    assert lan.host_name == "future host"


def test_lan_info_constructor_signature_accepts_compatibility_types() -> None:
    """LanInfo should advertise compatibility-friendly constructor annotations."""
    signature = inspect.signature(LanInfo)

    assert signature.parameters["mode"].annotation == LanMode | str
    assert signature.parameters["ip"].annotation == IpAddress | str
    assert signature.parameters["net_mask"].annotation == IpAddress | str
    assert signature.parameters["default_gateway"].annotation == IpAddress | str
    assert signature.parameters["dns"].annotation == IpAddress | str
    assert signature.parameters["mac"].annotation == MacAddress | str
    assert signature.parameters["host_name"].annotation == HostName | str


def test_info_group_struct_defaults() -> None:
    """InfoGroupStruct should default to an empty node list."""
    group = InfoGroupStruct()
    assert group.nodes == []
    assert group.raw_payload == {}


def test_info_group_defaults() -> None:
    """InfoGroup should keep the group identifier and default fields."""
    group = InfoGroup(group_id=4)
    assert group.group_id == 4
    assert group.nodes == []
    assert group.raw_payload == {}


def test_info_zone_group_defaults() -> None:
    """InfoZoneGroup should keep the typed zone and group identifiers."""
    group = InfoZoneGroup(zone_id=2, group_id=4)
    assert group.zone_id == 2
    assert group.group_id == 4
    assert group.nodes == []
    assert group.raw_payload == {}


def test_info_zone_struct_defaults() -> None:
    """InfoZoneStruct should default optional fields to empty values."""
    zone = InfoZoneStruct()
    assert zone.name is None
    assert zone.groups == []
    assert zone.raw_payload == {}


def test_info_zone_defaults() -> None:
    """InfoZone should expose the typed zone identifier and info fields."""
    zone = InfoZone(zone_id=2)
    assert zone.zone_id == 2
    assert zone.name is None
    assert zone.groups == []
    assert zone.raw_payload == {}


def test_info_zones_overview_defaults() -> None:
    """InfoZonesOverview should default zones to an empty list."""
    overview = InfoZonesOverview()
    assert overview.zones == []
    assert overview.raw_payload == {}


def test_config_group_struct_defaults() -> None:
    """ConfigGroupStruct should preserve an empty raw payload by default."""
    group = ConfigGroupStruct()
    assert group.raw_payload == {}


def test_config_group_struct_uses_identity_equality() -> None:
    """ConfigGroupStruct should not compare equal solely because it has no comparable fields."""
    assert ConfigGroupStruct() != ConfigGroupStruct()


def test_config_group_defaults() -> None:
    """ConfigGroup should keep the group identifier and default raw payload."""
    group = ConfigGroup(group_id=7)
    assert group.group_id == 7
    assert group.raw_payload == {}


def test_config_zone_struct_defaults() -> None:
    """ConfigZoneStruct should default optional fields to empty values."""
    zone = ConfigZoneStruct()
    assert zone.name is None
    assert zone.raw_payload == {}


def test_config_zone_uses_typed_name_and_groups() -> None:
    """ConfigZone should keep config names wrapped and groups typed."""
    group = ConfigGroup(group_id=3)
    zone = ConfigZone(
        zone_id=1,
        name=ConfigValueString(value="Living room"),
        groups=[group],
    )
    assert zone.zone_id == 1
    assert zone.name is not None
    assert zone.name.value == "Living room"
    assert zone.groups == [group]
    assert zone.raw_payload == {}


def test_config_zones_overview_defaults() -> None:
    """ConfigZonesOverview should default zones to an empty list."""
    overview = ConfigZonesOverview()
    assert overview.zones == []
    assert overview.raw_payload == {}


def test_node_sensor_info_defaults() -> None:
    """NodeSensorInfo should default all optional fields to None."""
    sensor = NodeSensorInfo()
    assert sensor.co2 is None
    assert sensor.iaq_co2 is None
    assert sensor.rh is None
    assert sensor.iaq_rh is None
    assert sensor.temp is None
    assert sensor.raw_payload == {}


def test_node_sensor_info_coerces_typed_primitives() -> None:
    """NodeSensorInfo should coerce stable scalar values into typed primitives."""
    sensor = NodeSensorInfo(co2=622, iaq_co2=84, rh=35.5, iaq_rh=81, temp=21.3)

    assert isinstance(sensor.co2, NodeCo2Ppm)
    assert isinstance(sensor.iaq_co2, NodeAirQualityIndex)
    assert isinstance(sensor.rh, NodeRelativeHumidity)
    assert isinstance(sensor.iaq_rh, NodeAirQualityIndex)
    assert isinstance(sensor.temp, NodeTemperature)

    signature = inspect.signature(NodeSensorInfo)
    assert signature.parameters["co2"].annotation == NodeCo2Ppm | int | None
    assert signature.parameters["iaq_co2"].annotation == NodeAirQualityIndex | int | None
    assert signature.parameters["rh"].annotation == NodeRelativeHumidity | float | None
    assert signature.parameters["iaq_rh"].annotation == NodeAirQualityIndex | int | None
    assert signature.parameters["temp"].annotation == NodeTemperature | float | None


def test_node_motor_state_info_defaults() -> None:
    """NodeMotorStateInfo should default all optional fields to None."""
    motor_state = NodeMotorStateInfo()
    assert motor_state.device_type is None
    assert motor_state.req is None
    assert motor_state.pos_req is None
    assert motor_state.pos is None
    assert motor_state.raw_payload == {}


def test_node_motor_state_info_coerces_typed_primitives() -> None:
    """NodeMotorStateInfo should coerce motor values into typed primitives."""
    motor_state = NodeMotorStateInfo(device_type=2, req=1, pos_req=150, pos=143)

    assert isinstance(motor_state.device_type, NodeMotorDeviceType)
    assert isinstance(motor_state.req, NodeMotorRequest)
    assert isinstance(motor_state.pos_req, NodeMotorPosition)
    assert isinstance(motor_state.pos, NodeMotorPosition)

    signature = inspect.signature(NodeMotorStateInfo)
    assert signature.parameters["device_type"].annotation == NodeMotorDeviceType | int | None
    assert signature.parameters["req"].annotation == NodeMotorRequest | int | None
    assert signature.parameters["pos_req"].annotation == NodeMotorPosition | int | None
    assert signature.parameters["pos"].annotation == NodeMotorPosition | int | None


def test_node_ventilation_info_flow_target_is_optional() -> None:
    """NodeVentilationInfo should allow omitted flow target."""
    ventilation = NodeVentilationInfo(
        state=VentilationState.CNT1,
        time_state_remain=0,
        time_state_end=0,
        mode=VentilationMode.NONE,
    )
    assert ventilation.flow_lvl_tgt is None
    assert ventilation.raw_payload == {}


def test_node_ventilation_info_coerces_typed_primitives() -> None:
    """NodeVentilationInfo should coerce enums and timer values cleanly."""
    ventilation = NodeVentilationInfo(
        state="CNT1",
        time_state_remain=1200,
        time_state_end=1778269000,
        mode="MANU",
        flow_lvl_tgt=100,
    )

    assert ventilation.state is VentilationState.CNT1
    assert ventilation.mode is VentilationMode.MANU
    assert isinstance(ventilation.time_state_remain, VentilationTimeRemaining)
    assert isinstance(ventilation.time_state_end, VentilationTimeEnd)
    assert isinstance(ventilation.flow_lvl_tgt, VentilationFlowLevelTarget)

    signature = inspect.signature(NodeVentilationInfo)
    assert signature.parameters["state"].annotation == VentilationState | str
    assert signature.parameters["mode"].annotation == VentilationMode | str
    assert signature.parameters["time_state_remain"].annotation == VentilationTimeRemaining | int
    assert signature.parameters["time_state_end"].annotation == VentilationTimeEnd | int
    assert (
        signature.parameters["flow_lvl_tgt"].annotation == VentilationFlowLevelTarget | int | None
    )


def test_node_general_info_coerces_typed_primitives() -> None:
    """NodeGeneralInfo should coerce stable general values into typed primitives."""
    general = NodeGeneralInfo(
        node_type="BOX",
        sub_type=1,
        network_type="VIRT",
        parent=0,
        asso=0,
        name="Kitchen",
        identify=0,
    )

    assert general.node_type is NodeType.BOX
    assert general.network_type is NetworkType.VIRT
    assert isinstance(general.sub_type, NodeSubtype)
    assert isinstance(general.parent, NodeParentId)
    assert isinstance(general.asso, NodeAssociationId)
    assert isinstance(general.name, NodeName)
    assert isinstance(general.identify, NodeIdentify)

    signature = inspect.signature(NodeGeneralInfo)
    assert signature.parameters["node_type"].annotation == NodeType | str
    assert signature.parameters["sub_type"].annotation == NodeSubtype | int
    assert signature.parameters["network_type"].annotation == NetworkType | str
    assert signature.parameters["parent"].annotation == NodeParentId | int
    assert signature.parameters["asso"].annotation == NodeAssociationId | int
    assert signature.parameters["name"].annotation == NodeName | str
    assert signature.parameters["identify"].annotation == NodeIdentify | int


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
    assert node.raw_payload == {}
    with pytest.raises(AttributeError):
        node.node_id = 2  # type: ignore[misc]


def test_network_type_values() -> None:
    """NetworkType should expose the documented public API values explicitly."""
    assert {network_type.value for network_type in NetworkType} == {
        "-",
        "WI",
        "RF",
        "VIRT",
        "MB",
        "UNKNOWN",
    }
    assert NetworkType.NONE.value == "-"
