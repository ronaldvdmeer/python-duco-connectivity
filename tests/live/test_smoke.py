"""Opt-in smoke tests against a live Duco device."""

from collections.abc import Callable

import pytest

from duco_connectivity import (
    BoardName,
    DiagStatus,
    DucoClient,
    DucoSerialNumber,
    DucoVersion,
    HostName,
    IpAddress,
    KnownLanMode,
    LanMode,
    MacAddress,
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


async def test_live_reads_diagnostics_and_nodes(
    live_client: DucoClient,
    live_report: Callable[[str], None],
) -> None:
    """Read diagnostics and node inventories from a live Duco device."""
    diagnostics = await live_client.async_get_diagnostics()
    nodes = await live_client.async_get_nodes()
    diagnostic_summary = ", ".join(
        f"{component.component}={component.status.value}" for component in diagnostics
    )
    sample_names = ", ".join(
        node.general.name if node.general.name else "<empty>" for node in nodes[:5]
    )

    live_report(
        f"diagnostics=[{diagnostic_summary}] nodes={len(nodes)} sample_names=[{sample_names}]"
    )

    assert diagnostics
    assert all(component.component for component in diagnostics)
    assert all(isinstance(component.status, DiagStatus) for component in diagnostics)
    assert nodes
    assert all(node.node_id > 0 for node in nodes)
    assert all(isinstance(node.general.name, str) for node in nodes)


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
    assert node_actions.nodes
    assert all(item.node_id > 0 for item in node_actions.nodes)
    assert all(action.action for item in node_actions.nodes for action in item.actions)
    assert all(zone.zone_id > 0 for zone in zones.zones)
    assert all(group.group_id > 0 for zone in zones.zones for group in zone.groups)
