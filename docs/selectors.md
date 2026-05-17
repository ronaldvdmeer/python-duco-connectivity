# Selector strategy

`python-duco-connectivity` uses a hybrid selector strategy for endpoint query
arguments like `module`, `submodule`, and `parameter`.

The goal is to keep the client close to the Duco public API while still making
the stable parts of that selector surface easier to discover and type-check.

## Core rule

- Use endpoint-specific known selector enums when the value set is already
  stable in the published Duco notes and the library already depends on that
  stability.
- Keep generic selector-taking methods open to raw strings so new firmware
  values remain reachable without waiting for a library release.
- Treat selector sets as endpoint-specific, not global. A selector that is
  stable for one endpoint family should not automatically become a shared
  project-wide enum.

## What is typed today

The library now exposes known selector enums for the stable module and
submodule sets used by the generic `/info`, generic `/config`, node-info, and
zone info/config endpoint families:

- `InfoModuleSelector`
- `InfoGeneralSubmoduleSelector`
- `ConfigModuleSelector`
- `ConfigGeneralSubmoduleSelector`
- `ConfigHeatRecoverySubmoduleSelector`
- `NodeInfoModuleSelector`
- `ZoneModuleSelector`
- `DeviceGroupConfigSubmoduleSelector`

These enums are hints, not closed registries. The same methods still accept raw
strings.

## What stays raw today

- Generic `parameter` selectors on `/info`, `/config`, node info, and zone
  info/config methods stay as raw strings.
- Raw node config helpers keep raw `parameter` strings because the typed node
  config models still intentionally cover only `Name`.
- Raw endpoint helpers like `async_get_raw()` remain the fallback when you need
  a path or selector set that the library does not model yet.

That boundary is deliberate. Parameter names tend to be broader, more granular,
and more firmware-dependent than the stable module families already reflected in
the typed model layer.

## Stable typed convenience methods

Some public methods already hide selectors entirely because they target a single
stable selector combination internally:

- `async_get_board_info()`
- `async_get_lan_info()`
- `async_get_diagnostics()`
- `async_get_write_requests_remaining()`

Those methods remain the preferred surface when they already describe the data
you need.

## Examples

Use a known selector enum when it matches the endpoint family you want:

```python
from duco_connectivity import (
    ConfigGeneralSubmoduleSelector,
    ConfigModuleSelector,
    DucoClient,
    InfoGeneralSubmoduleSelector,
    InfoModuleSelector,
)

payload = await client.async_get_info(
    module=InfoModuleSelector.GENERAL,
    submodule=InfoGeneralSubmoduleSelector.BOARD,
)

config = await client.async_get_config(
    module=ConfigModuleSelector.GENERAL,
    submodule=ConfigGeneralSubmoduleSelector.LAN,
    parameter="Mode",
)
```

Use a raw string when the library does not yet publish a stable enum for that
selector:

```python
payload = await client.async_get_zone_info(
    1,
    module="Groups",
    submodule="General",
    parameter="Nodes",
)
```

## Guidance for follow-up changes

Before promoting a selector set into a public enum, check all of the following:

- the selector family is scoped to a specific endpoint family
- the values are present in the published Duco notes or repeated observed
  payload trees
- the library already has typed models or convenience helpers that depend on
  those values being stable
- leaving the selector raw would materially reduce discoverability or typing
  value for callers

If those conditions are not met, keep the selector raw and document the reason
instead of forcing premature typing.