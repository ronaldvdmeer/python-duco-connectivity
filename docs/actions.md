# Action support

The Duco public API exposes both system-level action discovery through
`GET /action` and node-level action execution through
`POST /action/nodes/{node}`.

## System action discovery

`python-duco-connectivity` exposes system action discovery through
`DucoClient.async_get_actions()`.

Behavior:

- Calls `GET /action`
- Returns a typed `ActionItemList`
- Preserves the API-shaped `Action`, `ValType`, and optional `Enum` fields
- Falls back to `ActionValueType.UNKNOWN` when the device reports a future
  unmapped `ValType`

Example:

```python
from duco_connectivity import ActionValueType

actions = await client.async_get_actions()

for item in actions:
    if item.val_type is ActionValueType.ENUM:
        print(item.action, item.enum_values)
```

System-level `POST /action` execution is not exposed yet.

## Node action execution

`python-duco-connectivity` exposes generic node action execution through
`DucoClient.async_set_node_action(node_id, action, val=None)`.

Behavior:

- Sends the `Action` field exactly as requested
- Sends `Val` only when a value is provided
- Returns a typed `ActionResult`
- Preserves `async_set_ventilation_state()` as a convenience wrapper for
  `SetVentilationState`

The public model layer also exposes typed action request and discovery models
for the structures described in `notes/public_api_v2.5.yaml`:

- `Action` for system action request payloads
- `ActionNode` for node action request payloads
- `ActionItem` and `ActionItemList` for action discovery results
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
