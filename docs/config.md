# Generic config writes

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