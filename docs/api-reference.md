# API reference

This page is the compact inventory for the public `python-duco-connectivity` surface.
It is generated from the public exports in `src/duco_connectivity/__init__.py`
and the public async methods on `DucoClient`.

Regenerate it after public surface changes with:

```bash
python tools/api_reference.py write
```

## Navigation

- Start with the client construction rules if you need connection setup behavior.
- Use the method groups below to find the right entry point quickly.
- Use the topic links at the bottom when you need deeper examples or model detail.

## Client construction

- `DucoClient(session: ClientSession, host: str, *, port: int | None = None, request_timeout: float = 10.0) -> None`
- HTTP only: HTTPS is rejected intentionally.
- `host` must not include credentials, a path, a query string, or a fragment.
- Embedded host ports are allowed, but you cannot specify a port both inside `host` and via `port=`.
- Unbracketed IPv6 host values are rejected; use `[addr]` or `[addr]:port`.
- Invalid host input raises `ValueError` before any request is attempted.
- Request transport failures raise `DucoConnectionError`.
- HTTP error responses raise `DucoError`.
- Write-budget exhaustion raises `DucoWriteLimitError`.

## Client methods

### Core access

- `async_get_api_info() -> ApiInfo`
  - Endpoint: `GET /api`
  - Surface: typed
  - Summary: Return API metadata advertised by the box.
- `async_get_raw(path: str, *, params: dict[str, str] | None = None) -> Any`
  - Endpoint: `GET <api-relative path>`
  - Surface: raw escape hatch
  - Summary: Return the raw payload from an unmapped GET endpoint.
  - Details: [payload-preservation.md](payload-preservation.md)
  - Note: Use API-relative paths like `/info/nodes/7` and pass query arguments via `params`.
- `async_get_info(module: str | None = None, submodule: str | None = None, parameter: str | None = None) -> Any`
  - Endpoint: `GET /info`
  - Surface: raw escape hatch
  - Summary: Return the raw payload from the generic info endpoint.
  - Details: [payload-preservation.md](payload-preservation.md)
- `async_get_config(module: str | None = None, submodule: str | None = None, parameter: str | None = None) -> Config`
  - Endpoint: `GET /config`
  - Surface: typed
  - Summary: Return configuration values from the generic config endpoint.
  - Details: [config.md](config.md)
- `async_set_config(payload: dict[str, Any], module: str | None = None, submodule: str | None = None, parameter: str | None = None) -> Config`
  - Endpoint: `PATCH /config`
  - Surface: typed
  - Summary: Patch configuration values through the generic config endpoint.
  - Details: [config.md](config.md)
  - Note: Accepts sparse payloads built from `PatchConfigValue(...)` leaves or raw API-shaped `{'Val': ...}` objects.

### Actions and commands

- `async_get_actions() -> ActionItemList`
  - Endpoint: `GET /action`
  - Surface: typed
  - Summary: Return supported system actions reported by the local API.
  - Details: [actions.md](actions.md)
- `async_get_node_actions() -> NodeListActionItemList`
  - Endpoint: `GET /action/nodes`
  - Surface: typed
  - Summary: Return supported node actions reported by the local API.
  - Details: [actions.md](actions.md)
- `async_get_node_actions_for_node(node_id: int) -> NodeActionItemList`
  - Endpoint: `GET /action/nodes/{node}`
  - Surface: typed
  - Summary: Return supported actions for a specific node.
  - Details: [actions.md](actions.md)
- `async_set_action(action: str, val: str | int | bool | None = None) -> ActionResult`
  - Endpoint: `POST /action`
  - Surface: typed
  - Summary: Execute a generic system action through the local Duco API.
  - Details: [actions.md](actions.md)
- `async_set_ventilation_state(node_id: int, state: VentilationState | str) -> None`
  - Endpoint: `POST /action/nodes/{node}`
  - Surface: wrapper
  - Summary: Request a ventilation state change for a node.
  - Details: [actions.md](actions.md)
  - Note: Thin convenience wrapper over `async_set_node_action()` for `SetVentilationState`.
- `async_set_node_action(node_id: int, action: str, val: str | int | bool | None = None) -> ActionResult`
  - Endpoint: `POST /action/nodes/{node}`
  - Surface: typed
  - Summary: Execute a generic node action through the local Duco API.
  - Details: [actions.md](actions.md)

### Node configuration

- `async_get_node_configs_raw(parameter: str | None = None) -> Any`
  - Endpoint: `GET /config/nodes`
  - Surface: raw escape hatch
  - Summary: Return the raw payload from `/config/nodes`.
  - Details: [config.md](config.md)
- `async_get_node_config_raw(node_id: int, parameter: str | None = None) -> Any`
  - Endpoint: `GET /config/nodes/{node}`
  - Surface: raw escape hatch
  - Summary: Return the raw payload from `/config/nodes/{node}`.
  - Details: [config.md](config.md)
- `async_set_node_config_raw(node_id: int, payload: dict[str, Any], parameter: str | None = None) -> Any | None`
  - Endpoint: `PATCH /config/nodes/{node}`
  - Surface: raw escape hatch
  - Summary: Patch `/config/nodes/{node}` and return the raw API payload.
  - Details: [config.md](config.md)
  - Note: May return `None` when the box acknowledges the write without a JSON body.
- `async_get_node_configs(parameter: Literal['Name'] | None = None) -> ConfigNodeOverview`
  - Endpoint: `GET /config/nodes`
  - Surface: typed
  - Summary: Return node-level configuration values from `/config/nodes`.
  - Details: [config.md](config.md)
  - Note: The typed reader currently supports only `parameter='Name'`.
- `async_get_node_config(node_id: int, parameter: Literal['Name'] | None = None) -> ConfigNode`
  - Endpoint: `GET /config/nodes/{node}`
  - Surface: typed
  - Summary: Return node-level configuration values from `/config/nodes/{node}`.
  - Details: [config.md](config.md)
  - Note: The typed reader currently supports only `parameter='Name'`.
- `async_set_node_config(node_id: int, payload: dict[str, Any], parameter: Literal['Name'] = 'Name') -> ConfigNode`
  - Endpoint: `PATCH /config/nodes/{node}`
  - Surface: typed
  - Summary: Patch node-level configuration values through `/config/nodes/{node}`.
  - Details: [config.md](config.md)
  - Note: The typed writer always targets `parameter='Name'` so it can return a stable `ConfigNode`.

### Zone information and configuration

- `async_get_zones_config(zone: int | None = None, group: int | None = None, module: str | None = None, submodule: str | None = None, parameter: str | None = None) -> ConfigZonesOverview`
  - Endpoint: `GET /config/zones`
  - Surface: typed
  - Summary: Return zone-level configuration values from `/config/zones`.
  - Details: [zones.md](zones.md)
- `async_get_zone_config(zone_id: int, group: int | None = None, module: str | None = None, submodule: str | None = None, parameter: str | None = None) -> ConfigZone`
  - Endpoint: `GET /config/zones/{zone}`
  - Surface: typed
  - Summary: Return detailed configuration values for a specific zone.
  - Details: [zones.md](zones.md)
- `async_set_zone_config(zone_id: int, payload: dict[str, Any], module: str | None = None, submodule: str | None = None, parameter: str | None = None) -> ConfigZone`
  - Endpoint: `PATCH /config/zones/{zone}`
  - Surface: typed
  - Summary: Patch zone-level configuration values through `/config/zones/{zone}`.
  - Details: [zones.md](zones.md)
  - Note: Accepts sparse payloads built from `PatchConfigValue(...)` leaves or raw API-shaped `{'Val': ...}` objects.
- `async_get_zones_info() -> InfoZonesOverview`
  - Endpoint: `GET /info/zones`
  - Surface: typed
  - Summary: Return zone information reported by the local API.
  - Details: [zones.md](zones.md)
- `async_get_zone_info(zone_id: int, group: int | None = None, module: str | None = None, submodule: str | None = None, parameter: str | None = None) -> InfoZone`
  - Endpoint: `GET /info/zones/{zone}`
  - Surface: typed
  - Summary: Return detailed information for a specific zone.
  - Details: [zones.md](zones.md)
- `async_get_zone_group_info(zone_id: int, group_id: int, module: str | None = None, submodule: str | None = None, parameter: str | None = None) -> InfoZoneGroup`
  - Endpoint: `GET /info/zones/{zone}/groups/{group}`
  - Surface: typed
  - Summary: Return detailed information for a specific zone group.
  - Details: [zones.md](zones.md)

### Node and system information

- `async_get_board_info() -> BoardInfo`
  - Endpoint: `GET /info?module=General&submodule=Board`
  - Surface: typed
  - Summary: Return identity and version details for the main unit.
- `async_get_lan_info() -> LanInfo`
  - Endpoint: `GET /info?module=General&submodule=Lan`
  - Surface: typed
  - Summary: Return LAN settings reported by the box.
- `async_get_diagnostics() -> list[DiagComponent]`
  - Endpoint: `GET /info?module=Diag`
  - Surface: typed
  - Summary: Return health states for diagnostic subsystems.
- `async_get_nodes() -> list[Node]`
  - Endpoint: `GET /info/nodes`
  - Surface: typed
  - Summary: Return nodes reported by the local API.
  - Details: [nodes.md](nodes.md)
- `async_get_nodes_overview() -> list[NodeOverview]`
  - Endpoint: `GET /nodes`
  - Surface: typed
  - Summary: Return lightweight node identifiers reported by the local API.
  - Details: [nodes.md](nodes.md)
- `async_get_node_info(node_id: int, module: str | None = None, parameter: str | None = None) -> Node`
  - Endpoint: `GET /info/nodes/{node}`
  - Surface: typed
  - Summary: Return detailed information for a specific node.
  - Details: [nodes.md](nodes.md)
- `async_get_write_requests_remaining() -> int`
  - Endpoint: `GET /info?module=General&submodule=PublicApi`
  - Surface: typed
  - Summary: Return the remaining write budget reported by the box.

### Compatibility methods

- `async_get_write_req_remaining() -> int`
  - Endpoint: `Alias of async_get_write_requests_remaining()`
  - Surface: compatibility alias
  - Summary: Backward-compatible alias for the old write budget method name.
  - Note: Kept for callers still using the previous `python-duco-client` method name.

## Public exports

The package exports the following public symbols through `duco_connectivity.__all__`.

### Client

- `DucoClient`

### Models

- `Action`
- `ActionItem`
- `ActionItemList`
- `ActionNode`
- `ActionResult`
- `ApiEndpoint`
- `ApiInfo`
- `BoardInfo`
- `Config`
- `ConfigGroup`
- `ConfigGroupStruct`
- `ConfigNode`
- `ConfigNodeOverview`
- `ConfigNodeStruct`
- `ConfigSection`
- `ConfigValue`
- `ConfigValueOptions`
- `ConfigValueString`
- `ConfigZone`
- `ConfigZoneStruct`
- `ConfigZonesOverview`
- `DiagComponent`
- `InfoGroup`
- `InfoGroupStruct`
- `InfoZone`
- `InfoZoneGroup`
- `InfoZoneStruct`
- `InfoZonesOverview`
- `LanInfo`
- `Node`
- `NodeActionItemList`
- `NodeGeneralInfo`
- `NodeListActionItemList`
- `NodeMotorStateInfo`
- `NodeOverview`
- `NodeSensorInfo`
- `NodeVentilationInfo`
- `PatchConfigNodeValue`
- `PatchConfigValue`

### Enums

- `ActionResultStatus`
- `ActionValueType`
- `DiagStatus`
- `NetworkType`
- `NodeType`
- `VentilationMode`
- `VentilationState`

### Exceptions

- `DucoConnectionError`
- `DucoError`
- `DucoWriteLimitError`

### Other

- `__version__`

## Compatibility details

- `async_get_write_req_remaining()` delegates to `async_get_write_requests_remaining()`.
- `DucoRateLimitError` is a backward-compatible alias of `DucoWriteLimitError`.
- `ApiEndpointInfo` is a backward-compatible alias of `ApiEndpoint`.
- `ApiInfo(api_version=...)` and `ApiInfo.api_version` remain available for migration compatibility while the public field name is `public_api_version`.

## See also

- [config.md](config.md) for System, node, and zone config reads and writes
- [actions.md](actions.md) for System and node action discovery and execution
- [nodes.md](nodes.md) for Node models and node information readers
- [zones.md](zones.md) for Zone and group info and config models
- [ventilation-states.md](ventilation-states.md) for Ventilation enums and compatibility values
- [payload-preservation.md](payload-preservation.md) for Raw payload preservation and raw endpoint access
