# Config writes

## Generic config writes

The Duco public API exposes `PATCH /config` as the generic system config write
endpoint.

`python-duco-connectivity` exposes this through
`DucoClient.async_set_config(payload, module=None, submodule=None, parameter=None)`.

Behavior:

- Sends `PATCH /config`
- Forwards `module`, `submodule`, and `parameter` query arguments when provided
- Accepts sparse nested payloads that stay close to the API structure
- Accepts either `PatchConfigValue(...)` leaves or raw API-shaped `{"Val": ...}`
  leaf objects
- Returns a typed `Config` response

Example:

```python
from duco_connectivity import DucoClient, PatchConfigValue

payload = {
    "General": {
        "Lan": {
            "Mode": PatchConfigValue(value=2),
        }
    }
}

result = await client.async_set_config(
    payload,
    module="General",
    submodule="Lan",
    parameter="Mode",
)

mode = result.sections["General"].entries["Lan"].entries["Mode"]
```

When you already have an API-shaped payload, you can also pass wrapped leaves
directly:

```python
await client.async_set_config(
    {"General": {"Time": {"TimeZone": {"Val": 1}}}},
)

```

## Node config writes

The Duco public API also exposes `PATCH /config/nodes/{node}` for single-node
configuration changes.

`python-duco-connectivity` exposes this through
`DucoClient.async_set_node_config(node_id, payload, parameter=None)`.

Behavior:

- Sends `PATCH /config/nodes/{node}`
- Forwards the node path parameter directly
- Forwards `parameter` when provided; the typed writer currently supports only
    `Name`
- Accepts sparse payloads built from `PatchConfigNodeValue(...)` leaves or raw
    API-shaped `{"Val": ...}` leaf objects
- Returns a typed `ConfigNode` response

Example:

```python
from duco_connectivity import DucoClient, PatchConfigNodeValue

result = await client.async_set_node_config(
    7,
    {"Name": PatchConfigNodeValue(value="Kitchen valve")},
    parameter="Name",
)

assert result.node_id == 7
assert result.name is not None
assert result.name.value == "Kitchen valve"
```

When you already have an API-shaped payload, you can also pass wrapped leaves
directly:

```python
await client.async_set_node_config(
    7,
    {"Name": {"Val": "Kitchen valve"}},
)
```