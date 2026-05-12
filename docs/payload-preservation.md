# Raw payload preservation

`python-duco-connectivity` keeps typed models as the primary public API
surface, but many typed response models now also retain the original API
object in `raw_payload`.

This is intended as a forward-compatibility escape hatch:

- use the typed fields when the library already models the part of the payload
  you need
- use `raw_payload` when the Duco box exposes extra fields that the typed model
  layer does not yet represent
- use `async_get_raw()` when the endpoint itself is not modeled yet and you
  still need read-only access to the raw Duco response

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

`DucoClient.async_get_raw(path, *, params=None)` is the broader read-only
escape hatch for unmapped `GET` endpoints.

Use it when:

- you need an API-relative path that the client does not expose yet
- you need to inspect a new Duco `GET` payload before proposing a typed model

Keep these boundaries in mind:

- pass an API-relative path like `/nodes` or `/info/nodes/7`
- pass query arguments through `params`, not by embedding `?query=value` in the
  path
- prefer existing typed readers or endpoint-specific raw helpers when they
  already describe the endpoint you need more clearly
- this escape hatch is intentionally read-only; generic writes still stay on
  the typed and endpoint-specific public methods

## Example: unmapped endpoint read

```python
payload = await client.async_get_raw(
    "/info/nodes/7",
    params={"module": "Sensor", "parameter": "Temperature"},
)

temperature = payload["Temperature"]["Val"]
```
