# Action support

The Duco public API exposes `POST /action/nodes/{node}` as a generic node
action endpoint.

`python-duco-connectivity` exposes this through
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
