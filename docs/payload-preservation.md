# Raw payload preservation

`python-duco-connectivity` keeps typed models as the primary public API
surface, but many typed response models now also retain the original API
object in `raw_payload`.

This is intended as a forward-compatibility escape hatch:

- use the typed fields when the library already models the part of the payload
  you need
- use `raw_payload` when the Duco box exposes extra fields that the typed model
  layer does not yet represent

The preserved `raw_payload` keeps the original Duco API shape instead of a
second normalized structure.

## Example: unmapped node fields

```python
nodes = await client.async_get_nodes()

node = nodes[0]
firmware_family = node.general.raw_payload.get("FirmwareFamily")
voc = node.sensor.raw_payload.get("Voc") if node.sensor is not None else None
```

## Example: extra config metadata

```python
config = await client.async_get_config()

mode = config.sections["General"].entries["Lan"].entries["Mode"]
unit = mode.raw_payload.get("Unit")
```

## Scope

`raw_payload` is a best-effort compatibility aid on typed response models. It
does not replace the existing raw endpoint helpers like
`async_get_node_config_raw()` when you need a broader untyped endpoint surface.