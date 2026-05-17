# Config writes

## Generic config writes

The Duco public API exposes `PATCH /config` as the generic system config write
endpoint.

`python-duco-connectivity` exposes this through
`DucoClient.async_set_config(payload, module=None, submodule=None, parameter=None)`.

Selector inputs for `module` and `submodule` follow the endpoint-specific
strategy documented in [selectors.md](selectors.md). Known stable selector sets
are exposed as enums, while raw strings remain valid for forward compatibility.

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

When you already have an API-shaped payload, you can also pass the API-shaped
leaf objects directly:

```python
await client.async_set_config(
    {"General": {"Time": {"TimeZone": {"Val": 1}}}},
)

```

## Node config access

For node-level config endpoints, the client now exposes two layers:

- broader raw API access for any node config parameter through
    `async_get_node_configs_raw()`, `async_get_node_config_raw()`, and
    `async_set_node_config_raw()`
- stable typed `Name` helpers through `async_get_node_configs()`,
    `async_get_node_config()`, and `async_set_node_config()`

Use the raw methods when you need parameters that are not yet represented by
the typed `ConfigNode` models.

That boundary is deliberate: the typed node config helpers keep the stable
`Name` contract, while broader node config parameters remain raw-string
selectors. See [selectors.md](selectors.md) for the public rule.

Example:

```python
payload = await client.async_get_node_config_raw(7, parameter="FlowLvlTgt")
flow_target = payload["FlowLvlTgt"]["Val"]
```

## Node config writes

The Duco public API also exposes `PATCH /config/nodes/{node}` for single-node
configuration changes.

`python-duco-connectivity` exposes this through
`DucoClient.async_set_node_config(node_id, payload, parameter="Name")`.

For broader writes, use `DucoClient.async_set_node_config_raw(...)`.

Behavior of the raw writer:

- Sends `PATCH /config/nodes/{node}`
- Forwards any `parameter` query value unchanged when provided
- Accepts sparse payloads built from `PatchConfigNodeValue(...)` leaves or raw
    API-shaped `{"Val": ...}` leaf objects
- Returns the raw API payload when the box responds with JSON
- Returns `None` when the box acknowledges the write without a JSON body

Example:

```python
result = await client.async_set_node_config_raw(
        7,
        {"FlowLvlTgt": PatchConfigNodeValue(value=125)},
        parameter="FlowLvlTgt",
)

if result is not None:
        flow_target = result["FlowLvlTgt"]["Val"]
```

Behavior:

- Sends `PATCH /config/nodes/{node}`
- Forwards the node path parameter directly
- Always sends `parameter=Name` so the endpoint returns a payload that can be
    parsed as a typed `ConfigNode`
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

When you already have an API-shaped payload, you can also pass the API-shaped
leaf objects directly:

```python
await client.async_set_node_config(
    7,
    {"Name": {"Val": "Kitchen valve"}},
)
```

## Zone config writes

The Duco public API also exposes `PATCH /config/zones/{zone}` for single-zone
configuration changes.

`python-duco-connectivity` exposes this through
`DucoClient.async_set_zone_config(zone_id, payload, module=None, submodule=None, parameter=None)`.

Behavior:

- Sends `PATCH /config/zones/{zone}`
- Forwards the zone path parameter directly
- Forwards optional `module`, `submodule`, and `parameter` query values
- Accepts sparse payloads built from `PatchConfigValue(...)` leaves or raw
  API-shaped `{"Val": ...}` leaf objects
- Returns a typed `ConfigZone` response

Example:

```python
from duco_connectivity import DucoClient, PatchConfigValue

result = await client.async_set_zone_config(
    1,
    {
        "DeviceGroupConfig": {
            "General": {
                "Name": PatchConfigValue(value="Ground floor"),
            }
        }
    },
    module="DeviceGroupConfig",
    submodule="General",
    parameter="Name",
)

assert result.zone_id == 1
assert result.name is not None
assert result.name.value == "Ground floor"
```

When you already have an API-shaped payload, you can also pass the API-shaped
leaf objects directly:

```python
await client.async_set_zone_config(
    1,
    {"DeviceGroupConfig": {"General": {"Name": {"Val": "Ground floor"}}}},
)
```
