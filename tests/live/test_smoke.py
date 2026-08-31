"""Opt-in smoke tests against a live Duco device."""

from collections.abc import Callable

import pytest

from duco_connectivity import (
    ActionEnumValue,
    ActionName,
    BoardName,
    BypassSupplyTemperatureTarget,
    ConfigValue,
    ConfigValueString,
    DiagStatus,
    DucoClient,
    DucoSerialNumber,
    DucoUnsupportedCapabilityError,
    DucoVersion,
    HostName,
    IpAddress,
    KnownLanMode,
    LanMode,
    MacAddress,
    NetworkType,
    NodeAirQualityIndex,
    NodeCo2Ppm,
    NodeMotorDeviceType,
    NodeMotorPosition,
    NodeMotorRequest,
    NodeName,
    NodeRelativeHumidity,
    NodeTemperature,
    NodeType,
    VentilationFlowLevelTarget,
    VentilationMode,
    VentilationState,
    VentilationTemperatureInfo,
)

pytestmark = pytest.mark.live


async def test_live_reads_core_device_info(
    live_client: DucoClient,
    live_report: Callable[[str], None],
) -> None:
    """Read the core system endpoints from a live Duco device."""
    api_info = await live_client.async_get_api_info()
    board_info = await live_client.async_get_board_info()
    lan_info = await live_client.async_get_lan_info()
    remaining_writes = await live_client.async_get_write_requests_remaining()

    live_report(
        f"api={api_info.public_api_version} board={board_info.box_name} "
        f"lan_ip={lan_info.ip} writes_remaining={remaining_writes}"
    )

    assert isinstance(api_info.public_api_version, DucoVersion)
    assert api_info.public_api_version
    assert not api_info.endpoints or any(endpoint.url == "/api" for endpoint in api_info.endpoints)
    assert isinstance(board_info.box_name, BoardName)
    assert board_info.box_name
    assert isinstance(board_info.serial_board_comm, DucoSerialNumber)
    assert board_info.serial_board_comm
    assert board_info.time > 0
    assert isinstance(lan_info.mode, LanMode)
    assert lan_info.mode.known_value in {
        KnownLanMode.NO_CONNECTION,
        KnownLanMode.WIFI_AP,
        KnownLanMode.WIFI_CLIENT,
        KnownLanMode.ETHERNET,
    }
    assert isinstance(lan_info.ip, IpAddress)
    assert lan_info.ip
    assert isinstance(lan_info.mac, MacAddress)
    assert lan_info.mac
    assert isinstance(lan_info.host_name, HostName)
    assert lan_info.host_name
    assert remaining_writes >= 0


async def test_live_reads_typed_config_families(
    live_client: DucoClient,
    live_report: Callable[[str], None],
) -> None:
    """Read the stable typed config families from a live Duco device."""
    config = await live_client.async_get_config()
    general_present = config.general is not None
    heat_recovery_present = config.heat_recovery is not None

    live_report(
        f"config_general={general_present} config_heat_recovery={heat_recovery_present} "
        f"top_sections={','.join(sorted(config.sections))}"
    )

    assert config.sections

    if general_present:
        general = config.general
        assert general is not None
        if general.time is not None and general.time.time_zone is not None:
            assert isinstance(general.time.time_zone, ConfigValue)
        if general.lan is not None:
            if general.lan.mode is not None:
                assert isinstance(general.lan.mode, ConfigValue)
            if general.lan.static_ip is not None:
                assert isinstance(general.lan.static_ip, ConfigValueString)

    if heat_recovery_present:
        heat_recovery = config.heat_recovery
        assert heat_recovery is not None
        if heat_recovery.bypass is not None:
            for value in (
                heat_recovery.bypass.temp_sup_tgt_zone_1,
                heat_recovery.bypass.temp_sup_tgt_zone_2,
                heat_recovery.bypass.temp_sup_tgt_zone_3,
                heat_recovery.bypass.temp_sup_tgt_zone_4,
                heat_recovery.bypass.temp_sup_tgt_zone_5,
                heat_recovery.bypass.temp_sup_tgt_zone_6,
                heat_recovery.bypass.temp_sup_tgt_zone_7,
                heat_recovery.bypass.temp_sup_tgt_zone_8,
            ):
                if value is not None:
                    assert isinstance(value, ConfigValue)


async def test_live_reads_temperature_convenience_helpers(
    live_client: DucoClient,
    live_report: Callable[[str], None],
) -> None:
    """Read the temperature convenience helper surfaces from a live Duco device."""
    try:
        ventilation = await live_client.async_get_ventilation_temperature_info()
    except DucoUnsupportedCapabilityError:
        ventilation_summary = "unsupported"
    else:
        ventilation_summary = (
            f"oda={ventilation.temp_oda} sup={ventilation.temp_sup} "
            f"eta={ventilation.temp_eta} eha={ventilation.temp_eha}"
        )
        assert isinstance(ventilation, VentilationTemperatureInfo)
        for value in (
            ventilation.temp_oda,
            ventilation.temp_sup,
            ventilation.temp_eta,
            ventilation.temp_eha,
        ):
            if value is not None:
                assert isinstance(value, float)

    try:
        bypass = await live_client.async_get_bypass_supply_temperature_target(1)
    except DucoUnsupportedCapabilityError:
        bypass = None
        bypass_summary = "unsupported"
    else:
        bypass_summary = None if bypass is None else bypass.value

    live_report(f"ventilation_temps={ventilation_summary} bypass_zone1={bypass_summary}")

    if bypass is not None:
        assert isinstance(bypass, BypassSupplyTemperatureTarget)
        assert bypass.zone_id == 1
        assert isinstance(bypass.value, float)

    try:
        bypass_targets = await live_client.async_get_bypass_supply_temperature_targets()
    except DucoUnsupportedCapabilityError:
        bypass_targets_summary = "unsupported"
    else:
        bypass_targets_summary = ",".join(str(zone_id) for zone_id in bypass_targets)
        assert all(
            zone_id == target.zone_id and isinstance(target, BypassSupplyTemperatureTarget)
            for zone_id, target in bypass_targets.items()
        )

    live_report(f"bypass_zones={bypass_targets_summary}")


async def test_live_reads_diagnostics_and_nodes(
    live_client: DucoClient,
    live_report: Callable[[str], None],
) -> None:
    """Read diagnostics and node inventories from a live Duco device."""
    diagnostics = await live_client.async_get_diagnostics()
    nodes = await live_client.async_get_nodes()
    diagnostic_summary = ", ".join(
        f"{component.component}={component.raw_status}" for component in diagnostics
    )
    sample_names = ", ".join(
        node.general.name if node.general.name else "<empty>" for node in nodes[:5]
    )

    live_report(
        f"diagnostics=[{diagnostic_summary}] nodes={len(nodes)} sample_names=[{sample_names}]"
    )

    assert diagnostics
    assert all(component.component for component in diagnostics)
    assert all(
        component.status is None or isinstance(component.status, DiagStatus)
        for component in diagnostics
    )
    assert all(component.raw_status for component in diagnostics)
    assert nodes
    assert all(node.node_id > 0 for node in nodes)
    assert all(isinstance(node.general.node_type, NodeType) for node in nodes)
    assert all(isinstance(node.general.network_type, NetworkType) for node in nodes)
    assert all(isinstance(node.general.name, NodeName) for node in nodes)

    for node in nodes:
        if node.ventilation is not None:
            assert isinstance(node.ventilation.state, VentilationState)
            assert isinstance(node.ventilation.mode, VentilationMode)
            if node.ventilation.flow_lvl_tgt is not None:
                assert isinstance(node.ventilation.flow_lvl_tgt, VentilationFlowLevelTarget)
        if node.sensor is not None:
            if node.sensor.co2 is not None:
                assert isinstance(node.sensor.co2, NodeCo2Ppm)
            if node.sensor.iaq_co2 is not None:
                assert isinstance(node.sensor.iaq_co2, NodeAirQualityIndex)
            if node.sensor.rh is not None:
                assert isinstance(node.sensor.rh, NodeRelativeHumidity)
            if node.sensor.iaq_rh is not None:
                assert isinstance(node.sensor.iaq_rh, NodeAirQualityIndex)
            if node.sensor.temp is not None:
                assert isinstance(node.sensor.temp, NodeTemperature)
        if node.motor_state is not None:
            if node.motor_state.device_type is not None:
                assert isinstance(node.motor_state.device_type, NodeMotorDeviceType)
            if node.motor_state.req is not None:
                assert isinstance(node.motor_state.req, NodeMotorRequest)
            if node.motor_state.pos_req is not None:
                assert isinstance(node.motor_state.pos_req, NodeMotorPosition)
            if node.motor_state.pos is not None:
                assert isinstance(node.motor_state.pos, NodeMotorPosition)


async def test_live_reads_actions_and_zones(
    live_client: DucoClient,
    live_report: Callable[[str], None],
) -> None:
    """Read action discovery and zone info from a live Duco device."""
    actions = await live_client.async_get_actions()
    node_actions = await live_client.async_get_node_actions()
    zones = await live_client.async_get_zones_info()
    total_node_actions = sum(len(item.actions) for item in node_actions.nodes)

    live_report(
        f"system_actions={len(actions)} node_action_nodes={len(node_actions.nodes)} "
        f"node_actions={total_node_actions} zones={len(zones.zones)}"
    )

    assert actions
    assert all(item.action for item in actions)
    assert all(isinstance(item.action, ActionName) for item in actions)
    assert all(
        isinstance(enum_value, ActionEnumValue)
        for item in actions
        for enum_value in item.enum_values
    )
    assert node_actions.nodes
    assert all(item.node_id > 0 for item in node_actions.nodes)
    assert all(action.action for item in node_actions.nodes for action in item.actions)
    assert all(
        isinstance(action.action, ActionName)
        for item in node_actions.nodes
        for action in item.actions
    )
    assert all(
        isinstance(enum_value, ActionEnumValue)
        for item in node_actions.nodes
        for action in item.actions
        for enum_value in action.enum_values
    )
    assert all(zone.zone_id > 0 for zone in zones.zones)
    assert all(group.group_id > 0 for zone in zones.zones for group in zone.groups)
