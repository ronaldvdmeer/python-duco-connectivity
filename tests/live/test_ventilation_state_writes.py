"""Opt-in live tests for ventilation state writes."""

import asyncio
from collections.abc import Callable

import pytest

from duco_connectivity import DucoClient, VentilationState

pytestmark = [pytest.mark.live, pytest.mark.writes]


async def _wait_for_ventilation_state(
    live_client: DucoClient,
    node_id: int,
    expected_state: str,
    poll_attempts: int,
    poll_interval: float,
) -> str:
    """Poll a node until it reports the expected ventilation state."""
    current_state = ""

    for attempt in range(1, poll_attempts + 1):
        node = await live_client.async_get_node_info(node_id)
        if node.ventilation is None:
            pytest.fail(f"Node {node_id} does not report ventilation data")

        current_state = node.ventilation.state.value
        if current_state == expected_state:
            return current_state

        if attempt < poll_attempts:
            await asyncio.sleep(poll_interval)

    pytest.fail(
        f"Node {node_id} did not reach ventilation state {expected_state}; "
        f"last reported state was {current_state}"
    )


async def test_live_ventilation_state_round_trip(
    live_client: DucoClient,
    live_report: Callable[[str], None],
    live_ventilation_node_id: int,
    live_ventilation_target_states: tuple[str, ...],
    live_state_poll_attempts: int,
    live_state_poll_interval: float,
) -> None:
    """Round-trip a ventilation node through configured target states."""
    node_actions = await live_client.async_get_node_actions_for_node(live_ventilation_node_id)
    ventilation_action = next(
        (action for action in node_actions.actions if action.action == "SetVentilationState"),
        None,
    )
    if ventilation_action is None:
        pytest.skip(f"Node {live_ventilation_node_id} does not advertise SetVentilationState")

    supported_states = tuple(ventilation_action.enum_values)
    if not supported_states:
        pytest.skip(
            f"Node {live_ventilation_node_id} advertises SetVentilationState without enum values"
        )

    node = await live_client.async_get_node_info(live_ventilation_node_id)
    if node.ventilation is None:
        pytest.skip(f"Node {live_ventilation_node_id} does not report ventilation data")

    original_state = node.ventilation.state.value
    if original_state not in supported_states:
        pytest.skip(
            f"Original state {original_state} is not advertised as settable for node "
            f"{live_ventilation_node_id}"
        )

    requested_targets = tuple(
        state for state in live_ventilation_target_states if state in supported_states
    )
    if not requested_targets:
        pytest.skip(
            f"None of the requested target states {live_ventilation_target_states} are supported; "
            f"supported states are {supported_states}"
        )

    distinct_targets = tuple(state for state in requested_targets if state != original_state)
    if not distinct_targets:
        pytest.skip(
            "Requested states "
            f"{requested_targets} do not differ from original state {original_state}"
        )

    writes_before = await live_client.async_get_write_requests_remaining()
    minimum_required_writes = len(distinct_targets) + 1
    if writes_before < minimum_required_writes:
        pytest.skip(
            f"Need at least {minimum_required_writes} write requests for ventilation round-trip, "
            f"only {writes_before} remain"
        )

    validated_states: list[str] = []

    try:
        for target_state in distinct_targets:
            await live_client.async_set_ventilation_state(
                live_ventilation_node_id,
                VentilationState(target_state),
            )
            confirmed_state = await _wait_for_ventilation_state(
                live_client,
                live_ventilation_node_id,
                target_state,
                live_state_poll_attempts,
                live_state_poll_interval,
            )
            validated_states.append(confirmed_state)
            live_report(f"ventilation node={live_ventilation_node_id} reached={confirmed_state}")
    finally:
        await live_client.async_set_ventilation_state(
            live_ventilation_node_id,
            VentilationState(original_state),
        )
        restored_state = await _wait_for_ventilation_state(
            live_client,
            live_ventilation_node_id,
            original_state,
            live_state_poll_attempts,
            live_state_poll_interval,
        )
        live_report(f"ventilation node={live_ventilation_node_id} restored={restored_state}")

    writes_after = await live_client.async_get_write_requests_remaining()
    live_report(
        f"ventilation_round_trip node={live_ventilation_node_id} "
        f"original={original_state} validated={','.join(validated_states)} "
        f"writes_before={writes_before} writes_after={writes_after} "
        f"supported={','.join(supported_states)}"
    )
    assert validated_states == list(distinct_targets)
    assert 0 <= writes_after <= writes_before
