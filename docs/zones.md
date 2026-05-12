# Zone and group models

`python-duco-connectivity` exposes typed zone and group models that mirror the
published Duco `/info/zones` and `/config/zones` schema families.

The client does not expose typed zone read or write methods yet, but these
models provide the public data layer needed for that future endpoint work.

## Info models

- `InfoZonesOverview` wraps a list of `InfoZone` entries.
- `InfoZone` keeps the typed `zone_id`, an optional plain-string `name`, and a
  list of `InfoGroup` entries.
- `InfoGroup` keeps the typed `group_id` and the documented `nodes` list.
- `InfoZoneStruct` and `InfoGroupStruct` mirror the structural parts of the
  published schemas when you need the zone or group body without the outer
  identifier field.

## Config models

- `ConfigZonesOverview` wraps a list of `ConfigZone` entries.
- `ConfigZone` keeps the typed `zone_id`, an optional `ConfigValueString`
  `name`, and a list of `ConfigGroup` entries.
- `ConfigZoneStruct` mirrors the zone-body fields without the outer `Zone`
  identifier and is suitable for future typed zone config helpers.
- `ConfigGroupStruct` intentionally has no typed fields yet because the current
  public API note defines the struct as an empty object. The model still keeps
  `raw_payload` so newly observed fields remain inspectable without breaking the
  public surface.

## Raw payload preservation

Like the rest of the typed model layer, the zone and group models preserve the
original API object in `raw_payload` for forward compatibility.