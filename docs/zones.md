# Zone and group models

`python-duco-connectivity` exposes typed zone and group models that mirror the
published Duco `/info/zones` and `/config/zones` schema families.

`DucoClient.async_get_zones_config()` exposes typed `GET /config/zones`
support for the published zone config overview endpoint.
`DucoClient.async_get_zone_config()` exposes typed
`GET /config/zones/{zone}` support for the published single-zone config
endpoint.
`DucoClient.async_set_zone_config()` exposes typed
`PATCH /config/zones/{zone}` support for single-zone config writes.
`DucoClient.async_get_zones_info()` and `DucoClient.async_get_zone_info()`
expose typed `GET /info/zones` and `GET /info/zones/{zone}` support for the
published zone info endpoints.
`DucoClient.async_get_zone_group_info()` exposes typed
`GET /info/zones/{zone}/groups/{group}` support for the published group-level
zone info endpoint.

## Zone info readers

- `async_get_zones_info()` returns an `InfoZonesOverview`.
- `async_get_zone_info()` returns a single `InfoZone`.
- `async_get_zone_group_info()` returns a single `InfoZoneGroup`.
- Zone names are read from `DeviceGroupConfig.General.Name` and exposed as a
  plain string on `InfoZone.name`.
- Group node membership is read from `DeviceGroupConfig.General.Nodes` and
  exposed as a list of integers on `InfoGroup.nodes`.
- The zone-group reader forwards the documented optional `module`,
  `submodule`, and `parameter` query arguments unchanged.
- Unknown zone or group fields remain available through `raw_payload` for
  forward compatibility.
- The single-zone reader forwards the documented optional `group`, `module`,
  `submodule`, and `parameter` query arguments unchanged.

## Zone config readers

- `async_get_zones_config()` returns a `ConfigZonesOverview`.
- `async_get_zone_config()` returns a single `ConfigZone`.
- `async_set_zone_config()` returns a single `ConfigZone` after a successful
  patch.
- The zone config overview reader forwards the documented optional `zone`,
  `group`, `module`, `submodule`, and `parameter` query arguments unchanged.
- The single-zone config reader forwards the documented optional `group`,
  `module`, `submodule`, and `parameter` query arguments unchanged.
- The single-zone config writer forwards the documented optional `module`,
  `submodule`, and `parameter` query arguments unchanged.
- Zone config names stay wrapped as `ConfigValueString` because `/config`
  payloads keep the nested `{"Val": ...}` shape.
- Group entries currently expose only the typed `group_id`, while preserving
  the full raw group object for forward compatibility because the current
  public API note still defines an empty `ConfigGroupStruct`.

## Info models

- `InfoZonesOverview` wraps a list of `InfoZone` entries.
- `InfoZone` keeps the typed `zone_id`, an optional plain-string `name`, and a
  list of `InfoGroup` entries.
- `InfoGroup` keeps the typed `group_id` and the documented `nodes` list.
- `InfoZoneGroup` keeps the typed `zone_id`, `group_id`, and documented
  `nodes` list for the dedicated group endpoint.
- `InfoZoneStruct` and `InfoGroupStruct` mirror the structural parts of the
  published schemas when you need the zone or group body without the outer
  identifier field.

## Config models

- `ConfigZonesOverview` wraps a list of `ConfigZone` entries.
- `ConfigZone` keeps the typed `zone_id`, an optional `ConfigValueString`
  `name`, and a list of `ConfigGroup` entries.
- `ConfigZoneStruct` mirrors the zone-body fields without the outer `Zone`
  identifier and is reused by the typed single-zone config helper.
- `ConfigGroupStruct` intentionally has no typed fields yet because the current
  public API note defines the struct as an empty object. The model still keeps
  `raw_payload` so newly observed fields remain inspectable without breaking the
  public surface.

## Raw payload preservation

Like the rest of the typed model layer, the zone and group models preserve the
original API object in `raw_payload` for forward compatibility.
