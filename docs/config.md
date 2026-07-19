# Config reads and writes

## Generic config reads

The Duco public API exposes `GET /config` as the generic system config read
endpoint.

`python-duco-connectivity` exposes this through
`DucoClient.async_get_config(module=None, submodule=None, parameter=None)`.

Behavior:

- Returns a `Config` response with the generic `sections` tree preserved
- Also exposes stable typed families on `Config.general` and
    `Config.heat_recovery`
- Keeps unknown or not-yet-mapped branches available through `sections` and
    `raw_payload`
- Keeps generic config values in the raw API scale published by Duco, such as
    decicelsius-backed bypass targets under `HeatRecovery.Bypass`

Example:

```python
from duco_connectivity import ConfigValueOptions

config = await client.async_get_config()

if config.general is not None and config.general.lan is not None:
    mode = config.general.lan.mode
    if isinstance(mode, ConfigValueOptions):
        print(mode.value, mode.options)

raw_mode = config.sections["General"].entries["Lan"].entries["Mode"]
```

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
- Accepts typed `PatchConfig...` model families, `PatchConfigValue(...)` leaves,
  or raw API-shaped `{"Val": ...}` leaf objects
- Returns a typed `Config` response

Example:

```python
from duco_connectivity import (
    DucoClient,
    PatchConfig,
    PatchConfigGeneral,
    PatchConfigLan,
    PatchConfigValue,
)

payload = PatchConfig(
    general=PatchConfigGeneral(
        lan=PatchConfigLan(
            mode=PatchConfigValue(value=2),
        )
    )
)

result = await client.async_set_config(
    payload,
    module="General",
    submodule="Lan",
    parameter="Mode",
)

if result.general is not None and result.general.lan is not None:
    mode = result.general.lan.mode
```

When you already have an API-shaped payload, you can also pass the API-shaped
leaf objects directly:

```python
await client.async_set_config(
    {"General": {"Time": {"TimeZone": {"Val": 1}}}},
)

```

## Temperature convenience helpers

The generic `Config` models stay close to the raw Duco API payload. That means
typed `ConfigValue` leaves such as `HeatRecovery.Bypass.TempSupTgtZone1` keep
their integer API scale instead of converting automatically to Celsius.

For callers that want a narrower typed surface with the Celsius conversion kept
inside the library, `DucoClient` also exposes these convenience helpers:

- `async_get_bypass_supply_temperature_target(zone_id)`
- `async_set_bypass_supply_temperature_target(zone_id, temperature)`

Behavior:

- Reads and writes the same `HeatRecovery.Bypass.TempSupTgtZoneX` fields
- Accepts and returns Celsius values in `0.1°C` increments
- Raises `DucoUnsupportedCapabilityError` when the box explicitly reports that the optional target endpoint is unsupported
- Raises `DucoError` when a parameter-specific read returns a valid `/config` response without the requested target field
- Preserves the generic `async_get_config()` and `async_set_config()` behavior
    unchanged for callers that still want the original API-shaped payloads

Example:

```python
target = await client.async_get_bypass_supply_temperature_target(1)
print(target.value, target.minimum, target.increment, target.maximum)

updated = await client.async_set_bypass_supply_temperature_target(1, 18.5)
assert updated.value == 18.5
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
- Accepts `PatchConfigNodeStruct(...)`, sparse payloads built from
    `PatchConfigNodeValue(...)` leaves, or raw API-shaped `{"Val": ...}` leaf
    objects
- Returns a typed `ConfigNode` response

Example:

```python
from duco_connectivity import DucoClient, PatchConfigNodeStruct, PatchConfigNodeValue

result = await client.async_set_node_config(
    7,
    PatchConfigNodeStruct(name=PatchConfigNodeValue(value="Kitchen valve")),
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
- Accepts `PatchConfigZoneStruct(...)`, sparse payloads built from
    `PatchConfigValue(...)` leaves, or raw API-shaped `{"Val": ...}` leaf
    objects
- Returns a typed `ConfigZone` response

Example:

```python
from duco_connectivity import (
    DucoClient,
    PatchConfigValue,
    PatchConfigZoneDeviceGroupConfig,
    PatchConfigZoneGeneral,
    PatchConfigZoneStruct,
)

result = await client.async_set_zone_config(
    1,
    PatchConfigZoneStruct(
        device_group_config=PatchConfigZoneDeviceGroupConfig(
            general=PatchConfigZoneGeneral(
                name=PatchConfigValue(value="Ground floor"),
            )
        )
    ),
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
