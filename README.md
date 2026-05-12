# python-duco-connectivity

Async Python client for the local Duco HTTP API.

`python-duco-connectivity` is a small async client for the unauthenticated
local Duco HTTP endpoints that were validated during initial development. The
library keeps its public models close to the API payload shape and is intended
to stay reusable outside Home Assistant.

## Installation

Until the first PyPI release is published, install directly from GitHub:

```bash
pip install git+https://github.com/ronaldvdmeer/python-duco-connectivity.git
```

After the package is published on PyPI, install it with:

```bash
pip install python-duco-connectivity
```

## Current scope

- HTTP only
- asynchronous communication via `aiohttp`
- typed models that stay close to the API response shape

## Public API surface

The current client exposes:

- `async_get_api_info()` for `GET /api`
- `async_get_info()` for generic `GET /info` access with optional `module`, `submodule`, and `parameter` query arguments
- `async_get_config()` for generic `GET /config` access with optional `module`, `submodule`, and `parameter` query arguments
- `async_set_config()` for generic `PATCH /config` access with optional `module`, `submodule`, and `parameter` query arguments plus sparse config payloads built from `PatchConfigValue` leaves or raw API-shaped `{"Val": ...}` objects
- `async_get_node_configs_raw()` for broader raw `GET /config/nodes` access with any `parameter` value
- `async_get_node_config_raw()` for broader raw `GET /config/nodes/{node}` access with any `parameter` value
- `async_set_node_config_raw()` for broader raw `PATCH /config/nodes/{node}` access with any `parameter` value; when the API acknowledges a write without a JSON body, this method returns `None`
- `async_get_node_configs()` for `GET /config/nodes`; when `parameter` is provided, the typed reader currently supports only `Name`
- `async_get_node_config()` for `GET /config/nodes/{node}`; when `parameter` is provided, the typed reader currently supports only `Name`
- `async_set_node_config()` for `PATCH /config/nodes/{node}`; the typed writer always requests `parameter=Name` so it can return a `ConfigNode`, and accepts sparse payloads built from `PatchConfigNodeValue` leaves or raw API-shaped `{"Val": ...}` objects
- `async_get_board_info()` for `GET /info?module=General&submodule=Board`
- `async_get_lan_info()` for `GET /info?module=General&submodule=Lan`
- `async_get_nodes_overview()` for `GET /nodes` when you only need lightweight node IDs
- `async_get_nodes()` for `GET /info/nodes`
- `async_get_node_info()` for `GET /info/nodes/{node}` with optional `module` and `parameter` query arguments
- `async_get_diagnostics()` for `GET /info?module=Diag`
- `async_get_write_requests_remaining()` for `GET /info?module=General&submodule=PublicApi`
- `async_get_actions()` for typed `GET /action` system action discovery
- `async_set_action()` for generic `POST /action` execution with a typed action result
- `async_get_node_actions()` for typed `GET /action/nodes` node action discovery
- `async_get_node_actions_for_node()` for typed `GET /action/nodes/{node}` per-node action discovery
- `async_set_node_action()` for generic `POST /action/nodes/{node}` execution with a typed action result
- `async_set_ventilation_state()` for `POST /action/nodes/{node}` with `SetVentilationState`

The focused convenience readers remain available for the payloads that the
library already models explicitly.

Node config access is split between broader raw API access and the existing
typed `Name` helpers. Use the `*_raw()` methods when you need non-`Name`
parameters like `FlowLvlTgt`, and use the typed helpers when you want a stable
`ConfigNode` or `ConfigNodeOverview` response.

Use `async_get_nodes_overview()` when you only need the lightweight node list
from `GET /nodes`, and `async_get_nodes()` when you need the richer
`GET /info/nodes` payload with general, ventilation, and sensor details.

`async_set_ventilation_state()` remains available as a thin convenience wrapper
over `async_set_node_action()` for callers that only need the existing
ventilation state write.

Use `async_get_actions()` when you need to inspect which system-level actions
the box exposes before attempting higher-level workflows. The returned
`ActionItem` entries preserve the API-shaped `Action`, `ValType`, and optional
`Enum` fields, with `ActionValueType.UNKNOWN` reserved for future unmapped
value kinds.

Use `async_set_action()` when you need to execute a system-level action through
`POST /action`. The method keeps the request body close to the API by sending
`Action` plus an optional `Val`, and it returns a typed `ActionResult`.

Use `async_get_node_actions()` when you need to inspect node-level action
capabilities across all reported nodes. The typed response keeps the API's
nested `Nodes` and per-node `Actions` structure via `NodeListActionItemList`
and `NodeActionItemList`, while reusing `ActionItem` for the leaf action
definitions.

Use `async_get_node_actions_for_node()` when you only need the discovery data
for one node. The typed response returns the same `NodeActionItemList` wrapper
used inside the broader `async_get_node_actions()` result, so callers can keep
one consistent per-node model regardless of which discovery endpoint they use.

The model layer includes `Action`, `ActionNode`, `ActionItem`,
`ActionItemList`, `ActionResult`, `ApiInfo`, `BoardInfo`, `Config`,
`ConfigNode`, `ConfigNodeOverview`, `ConfigNodeStruct`, `ConfigSection`,
`ConfigValue`, `ConfigValueOptions`, `ConfigValueString`,
`NodeActionItemList`, `NodeListActionItemList`, `PatchConfigValue`,
`PatchConfigNodeValue`, `LanInfo`, `Node`, `NodeOverview`,
`NodeGeneralInfo`, `NodeVentilationInfo`, and `NodeSensorInfo`.
The typed enum layer keeps `NodeType` closely aligned with the Duco public API
notes while preserving `UNKNOWN` as a fallback for future unmapped values.
Action discovery also exposes `ActionValueType` for the `ValType` values
described in the public API notes.

`VentilationState` keeps the documented public-note values, including the
explicit `"-"` state via `VentilationState.NONE`, while also retaining timed
manual compatibility values such as `MAN3x2` that have appeared in Duco
payloads and action discovery responses. More detail is available in
`docs/ventilation-states.md`.

More detail for action discovery plus system and node action execution is
available in `docs/actions.md`.
System and node config writes are documented in `docs/config.md`.

## Development

Install the development dependencies and run the same checks as CI:

```bash
pip install ".[dev]"
pytest
ruff check src tests
ruff format --check src tests
mypy src
bandit -r src -ll
pip-audit --desc on
```

## Validation

The current API surface was validated against a real Duco box during the first
development pass, covering:

- `GET /api`
- `GET /info` with generic module, submodule, and parameter queries
- `GET /config` with generic module, submodule, and parameter queries
- `PATCH /config` with a no-op `TimeZone` write against the current value
- `GET /info?module=General&submodule=Board`
- `GET /info?module=General&submodule=Lan`
- `GET /info/nodes`
- `GET /info?module=General&submodule=PublicApi`
- `POST /action/nodes/{node}` with a no-op `SetVentilationState`
