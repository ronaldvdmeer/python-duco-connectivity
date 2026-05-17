# Action support

The Duco public API exposes system-level action discovery through `GET /action`,
system-level action execution through `POST /action`, node-level action
discovery through `GET /action/nodes`, per-node action discovery through
`GET /action/nodes/{node}`, and node-level action execution through
`POST /action/nodes/{node}`.

## System action discovery

`python-duco-connectivity` exposes system action discovery through
`DucoClient.async_get_actions()`.

Behavior:

- Calls `GET /action`
- Returns a typed `ActionItemList`
- Types action names as `ActionName`
- Types enum-backed discovery values as `ActionEnumValue`
- Preserves the API-shaped `Action`, `ValType`, and optional `Enum` fields
- Falls back to `ActionValueType.UNKNOWN` when the device reports a future
  unmapped `ValType`
- Preserves future action names as string-compatible `ActionName` values with
  `known_value is None`

Example:

```python
from duco_connectivity import ActionValueType, KnownActionName

actions = await client.async_get_actions()

for item in actions:
    if item.action.known_value is KnownActionName.SET_WIFI_AP_MODE:
        print(item.action, item.enum_values)
    if item.val_type is ActionValueType.ENUM:
        print(item.action, item.enum_values)
```

## System action execution

`python-duco-connectivity` exposes generic system action execution through
`DucoClient.async_set_action(action, val=None)`.

Behavior:

- Accepts an `ActionName` or plain string for the `Action` field
- Sends the `Action` field exactly as requested
- Sends `Val` only when a value is provided
- Keeps `Val` open as `str | int | bool` because the Duco API only defines a
  small stable action-name set, not a single closed value domain
- Returns a typed `ActionResult`
- Reuses the same action-result contract as node action execution

Example:

```python
from duco_connectivity import ActionName, ActionResultStatus

result = await client.async_set_action(ActionName("SetIdentify"))

if result.result is ActionResultStatus.SUCCESS:
    ...
```

## Node action discovery

`python-duco-connectivity` exposes node action discovery through
`DucoClient.async_get_node_actions()`.

Behavior:

- Calls `GET /action/nodes`
- Returns a typed `NodeListActionItemList`
- Types action names as `ActionName`
- Types enum-backed discovery values as `ActionEnumValue`
- Preserves the nested API structure of `Nodes`, `Node`, and `Actions`
- Reuses `ActionItem` for each per-node action definition
- Falls back to `ActionValueType.UNKNOWN` when the device reports a future
  unmapped `ValType`

Example:

```python
node_actions = await client.async_get_node_actions()

for node in node_actions.nodes:
    print(node.node_id, [item.action for item in node.actions])
```

## Per-node action discovery

`python-duco-connectivity` exposes per-node action discovery through
`DucoClient.async_get_node_actions_for_node(node_id)`.

Behavior:

- Calls `GET /action/nodes/{node}`
- Returns a typed `NodeActionItemList`
- Types action names as `ActionName`
- Types enum-backed discovery values as `ActionEnumValue`
- Reuses `ActionItem` for each per-node action definition
- Falls back to `ActionValueType.UNKNOWN` when the device reports a future
  unmapped `ValType`

Example:

```python
node_actions = await client.async_get_node_actions_for_node(7)

print(node_actions.node_id, [item.action for item in node_actions.actions])
```

## Node action execution

`python-duco-connectivity` exposes generic node action execution through
`DucoClient.async_set_node_action(node_id, action, val=None)`.

Behavior:

- Accepts an `ActionName` or plain string for the `Action` field
- Sends the `Action` field exactly as requested
- Sends `Val` only when a value is provided
- Keeps `Val` open as `str | int | bool` because node action values are only
  partially specified in the published notes
- Returns a typed `ActionResult`
- Preserves `async_set_ventilation_state()` as a convenience wrapper for
  `SetVentilationState`

The public model layer also exposes typed action request and discovery models
for the structures described in `notes/public_api_v2.5.yaml`:

- `Action` for system action request payloads
- `ActionNode` for node action request payloads
- `ActionName` and `KnownActionName` for action-name typing with forward-
  compatible plain-string behavior
- `ActionEnumValue` for discovered enum-backed action options
- `ActionItem` and `ActionItemList` for action discovery results
- `ActionResult` and `ActionResultStatus` for action execution results
- `NodeActionItemList` and `NodeListActionItemList` for node-scoped action
  discovery results
- `ActionValueType` for the `ValType` enum values used in action discovery

Example:

```python
from duco_connectivity import ActionResultStatus, DucoClient

result = await client.async_set_node_action(1, "SetIdentify")

if result.result is ActionResultStatus.SUCCESS:
    ...
```

For ventilation state writes, the existing helper remains available:

```python
await client.async_set_ventilation_state(1, "MAN2")
```
