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
- HTTP error responses raise `DucoResponseError`, a `DucoError` subclass that exposes `status`, `path`, and `body`.
- Write-budget exhaustion raises `DucoWriteLimitError`, a `DucoResponseError` subclass with status `429`.

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
- `async_get_info(module: InfoModuleSelector | str | None = None, submodule: InfoGeneralSubmoduleSelector | str | None = None, parameter: str | None = None) -> Any`
  - Endpoint: `GET /info`
  - Surface: raw escape hatch
  - Summary: Return the raw payload from the generic info endpoint.
  - Details: [payload-preservation.md](payload-preservation.md)
- `async_get_config(module: ConfigModuleSelector | str | None = None, submodule: ConfigGeneralSubmoduleSelector | ConfigHeatRecoverySubmoduleSelector | str | None = None, parameter: str | None = None) -> Config`
  - Endpoint: `GET /config`
  - Surface: typed
  - Summary: Return configuration values from the generic config endpoint.
  - Details: [config.md](config.md)
- `async_set_config(payload: dict[str, Any] | PatchConfigModel, module: ConfigModuleSelector | str | None = None, submodule: ConfigGeneralSubmoduleSelector | ConfigHeatRecoverySubmoduleSelector | str | None = None, parameter: str | None = None) -> Config`
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
- `async_set_action(action: ActionName | str, val: str | int | bool | None = None) -> ActionResult`
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
- `async_set_node_action(node_id: int, action: ActionName | str, val: str | int | bool | None = None) -> ActionResult`
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
- `async_set_node_config(node_id: int, payload: dict[str, Any] | PatchConfigNodeStruct, parameter: Literal['Name'] = 'Name') -> ConfigNode`
  - Endpoint: `PATCH /config/nodes/{node}`
  - Surface: typed
  - Summary: Patch node-level configuration values through `/config/nodes/{node}`.
  - Details: [config.md](config.md)
  - Note: The typed writer always targets `parameter='Name'` so it can return a stable `ConfigNode`.

### Zone information and configuration

- `async_get_zones_config(zone: int | None = None, group: int | None = None, module: ZoneModuleSelector | str | None = None, submodule: DeviceGroupConfigSubmoduleSelector | str | None = None, parameter: str | None = None) -> ConfigZonesOverview`
  - Endpoint: `GET /config/zones`
  - Surface: typed
  - Summary: Return zone-level configuration values from `/config/zones`.
  - Details: [zones.md](zones.md)
- `async_get_zone_config(zone_id: int, group: int | None = None, module: ZoneModuleSelector | str | None = None, submodule: DeviceGroupConfigSubmoduleSelector | str | None = None, parameter: str | None = None) -> ConfigZone`
  - Endpoint: `GET /config/zones/{zone}`
  - Surface: typed
  - Summary: Return detailed configuration values for a specific zone.
  - Details: [zones.md](zones.md)
- `async_set_zone_config(zone_id: int, payload: dict[str, Any] | PatchConfigZoneStruct, module: ZoneModuleSelector | str | None = None, submodule: DeviceGroupConfigSubmoduleSelector | str | None = None, parameter: str | None = None) -> ConfigZone`
  - Endpoint: `PATCH /config/zones/{zone}`
  - Surface: typed
  - Summary: Patch zone-level configuration values through `/config/zones/{zone}`.
  - Details: [zones.md](zones.md)
  - Note: Accepts `PatchConfigZoneStruct(...)`, sparse payloads built from `PatchConfigValue(...)` leaves, or raw API-shaped `{'Val': ...}` objects.
- `async_get_zones_info() -> InfoZonesOverview`
  - Endpoint: `GET /info/zones`
  - Surface: typed
  - Summary: Return zone information reported by the local API.
  - Details: [zones.md](zones.md)
- `async_get_zone_info(zone_id: int, group: int | None = None, module: ZoneModuleSelector | str | None = None, submodule: DeviceGroupConfigSubmoduleSelector | str | None = None, parameter: str | None = None) -> InfoZone`
  - Endpoint: `GET /info/zones/{zone}`
  - Surface: typed
  - Summary: Return detailed information for a specific zone.
  - Details: [zones.md](zones.md)
- `async_get_zone_group_info(zone_id: int, group_id: int, module: ZoneModuleSelector | str | None = None, submodule: DeviceGroupConfigSubmoduleSelector | str | None = None, parameter: str | None = None) -> InfoZoneGroup`
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
- `async_get_diagnostics_info() -> DiagInfo`
  - Endpoint: `GET /info?module=Diag`
  - Surface: typed
  - Summary: Return diagnostic subsystem details reported by the box.
- `async_get_diagnostics() -> list[DiagComponent]`
  - Endpoint: `GET /info?module=Diag`
  - Surface: typed
  - Summary: Return health states for diagnostic subsystems.
- `async_get_time_filter_remaining() -> int | None`
  - Endpoint: `GET /info?module=HeatRecovery`
  - Surface: typed
  - Summary: Return the remaining heat recovery filter time when the box reports it.
- `async_get_ventilation_temperature_info() -> VentilationTemperatureInfo`
  - Endpoint: `GET /info?module=Ventilation`
  - Surface: wrapper
  - Summary: Return ventilation temperatures when the box exposes them, in Celsius.
  - Note: Converts the raw Duco decicelsius ventilation sensor values to Celsius.
  - Note: Raises `DucoUnsupportedCapabilityError` when the box reports the optional endpoint as unsupported.
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
- `async_get_node_info(node_id: int, module: NodeInfoModuleSelector | str | None = None, parameter: str | None = None) -> Node`
  - Endpoint: `GET /info/nodes/{node}`
  - Surface: typed
  - Summary: Return detailed information for a specific node.
  - Details: [nodes.md](nodes.md)
- `async_get_write_requests_remaining() -> int`
  - Endpoint: `GET /info?module=General&submodule=PublicApi`
  - Surface: typed
  - Summary: Return the remaining write budget reported by the box.
- `async_get_bypass_supply_temperature_target(zone_id: int) -> BypassSupplyTemperatureTarget`
  - Endpoint: `GET /config?module=HeatRecovery&submodule=Bypass&parameter=TempSupTgtZone{zone}`
  - Surface: wrapper
  - Summary: Return a bypass supply target from `/config` in Celsius.
  - Details: [config.md](config.md)
  - Note: Returns a Celsius convenience model while leaving the generic ConfigValue surface unchanged.
  - Note: Raises `DucoUnsupportedCapabilityError` when the requested optional target endpoint is unsupported.
  - Note: Raises `DucoError` when a parameter-specific read succeeds without the requested target field in the response.
- `async_get_bypass_supply_temperature_targets() -> dict[int, BypassSupplyTemperatureTarget]`
  - Endpoint: `GET /config?module=HeatRecovery&submodule=Bypass`
  - Surface: wrapper
  - Summary: Return all bypass supply targets exposed through `/config` in Celsius.
  - Details: [config.md](config.md)
  - Note: Returns all available bypass supply targets as Celsius convenience models.
  - Note: Omits target fields that are absent from a successful response.
  - Note: Raises `DucoUnsupportedCapabilityError` when the optional bypass endpoint is unsupported.
- `async_set_bypass_supply_temperature_target(zone_id: int, temperature: float) -> BypassSupplyTemperatureTarget`
  - Endpoint: `PATCH /config?module=HeatRecovery&submodule=Bypass&parameter=TempSupTgtZone{zone}`
  - Surface: wrapper
  - Summary: Set a bypass supply target through `/config` using Celsius input.
  - Details: [config.md](config.md)
  - Note: Accepts Celsius input in 0.1°C increments and serializes it back to the raw Duco decicelsius payload.

## Public exports

The package exports the following public symbols through `duco_connectivity.__all__`.

### Client

- `DucoClient`

### Models

- `Action`
- `ActionEnumValue`
- `ActionItem`
- `ActionItemList`
- `ActionName`
- `ActionNode`
- `ActionResult`
- `ApiEndpoint`
- `ApiInfo`
- `BoardInfo`
- `BoardName`
- `BypassSupplyTemperatureTarget`
- `Config`
- `ConfigAutoRebootComm`
- `ConfigGeneral`
- `ConfigGroup`
- `ConfigGroupStruct`
- `ConfigHeatRecovery`
- `ConfigHeatRecoveryBypass`
- `ConfigLan`
- `ConfigModbus`
- `ConfigNode`
- `ConfigNodeOverview`
- `ConfigNodeStruct`
- `ConfigSection`
- `ConfigTime`
- `ConfigValue`
- `ConfigValueOptions`
- `ConfigValueString`
- `ConfigZone`
- `ConfigZoneStruct`
- `ConfigZoneWithGroupStruct`
- `ConfigZonesOverview`
- `DiagComponent`
- `DiagInfo`
- `DucoSerialNumber`
- `DucoVersion`
- `HostName`
- `InfoGroup`
- `InfoGroupStruct`
- `InfoZone`
- `InfoZoneGroup`
- `InfoZoneStruct`
- `InfoZonesOverview`
- `IpAddress`
- `LanInfo`
- `LanMode`
- `MacAddress`
- `Node`
- `NodeActionItemList`
- `NodeAirQualityIndex`
- `NodeAssociationId`
- `NodeCo2Ppm`
- `NodeGeneralInfo`
- `NodeIdentify`
- `NodeListActionItemList`
- `NodeMotorDeviceType`
- `NodeMotorPosition`
- `NodeMotorRequest`
- `NodeMotorStateInfo`
- `NodeName`
- `NodeOverview`
- `NodeParentId`
- `NodeRelativeHumidity`
- `NodeSensorInfo`
- `NodeSubtype`
- `NodeTemperature`
- `NodeVentilationInfo`
- `PatchConfig`
- `PatchConfigAutoRebootComm`
- `PatchConfigGeneral`
- `PatchConfigHeatRecovery`
- `PatchConfigHeatRecoveryBypass`
- `PatchConfigLan`
- `PatchConfigModbus`
- `PatchConfigModel`
- `PatchConfigNodeStruct`
- `PatchConfigNodeValue`
- `PatchConfigTime`
- `PatchConfigValue`
- `PatchConfigZoneDeviceGroupConfig`
- `PatchConfigZoneGeneral`
- `PatchConfigZoneStruct`
- `VentilationFlowLevelTarget`
- `VentilationTemperatureInfo`
- `VentilationTimeEnd`
- `VentilationTimeRemaining`

### Enums

- `ActionResultStatus`
- `ActionValueType`
- `ConfigGeneralSubmoduleSelector`
- `ConfigHeatRecoverySubmoduleSelector`
- `ConfigModuleSelector`
- `DeviceGroupConfigSubmoduleSelector`
- `InfoGeneralSubmoduleSelector`
- `InfoModuleSelector`
- `KnownActionName`
- `KnownBoardName`
- `KnownLanMode`
- `NetworkType`
- `NodeInfoModuleSelector`
- `NodeType`
- `VentilationMode`
- `VentilationState`
- `ZoneModuleSelector`

### Exceptions

- `DucoConnectionError`
- `DucoError`
- `DucoResponseError`
- `DucoUnsupportedCapabilityError`
- `DucoWriteLimitError`

### Compatibility exports

- `ApiEndpointInfo`
- `DucoRateLimitError`

### Other

- `__version__`

## Compatibility details

- `DucoRateLimitError` is a backward-compatible alias of `DucoWriteLimitError`.
- `ApiEndpointInfo` is a backward-compatible alias of `ApiEndpoint`.
- `ApiInfo(api_version=...)` and `ApiInfo.api_version` remain available for migration compatibility while the public field name is `public_api_version`.
- `BoardName`, `DucoVersion`, `DucoSerialNumber`, `LanMode`, `IpAddress`, `MacAddress`, `HostName`, and the node scalar families like `NodeName`, `NodeSubtype`, `VentilationTimeRemaining`, and `NodeCo2Ppm` use string- or number-compatible typed primitives, so existing comparisons and JSON serialization continue to work while making the public metadata contract more explicit.

## See also

- [config.md](config.md) for System, node, and zone config reads and writes
- [actions.md](actions.md) for System and node action discovery and execution
- [nodes.md](nodes.md) for Node models and node information readers
- [selectors.md](selectors.md) for Selector strategy and known selector enums
- [zones.md](zones.md) for Zone and group info and config models
- [ventilation-states.md](ventilation-states.md) for Ventilation enums and compatibility values
- [payload-preservation.md](payload-preservation.md) for Raw payload preservation and raw endpoint access
