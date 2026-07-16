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

The package also installs a `duco-probe` CLI and supports module execution for
quick function probes against a local Duco box. When you are not running inside
an activated virtual environment, use the explicit `.venv/bin/...` paths shown
in the development examples below.

## Current scope

- HTTP only
- asynchronous communication via `aiohttp`
- typed stable config families for the documented `/config` branches
- typed helpers for stable `/info` fields such as heat recovery filter time
- optional temperature helpers that return `None` when the box reports their
  endpoint as unavailable
- typed models that stay close to the API response shape
- preserved `raw_payload` data on typed response models for forward compatibility

Diagnostic subsystem reads now keep raw component and status strings from
`Diag.SubSystems`, so future subsystem names or status values remain available
to downstream consumers without parse fallbacks or product-specific filtering.

## Getting started

```python
import asyncio

import aiohttp

from duco_connectivity import DucoClient


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        client = DucoClient(session, "192.168.1.10")
        api_info = await client.async_get_api_info()
        nodes = await client.async_get_nodes_overview()

        print(api_info.public_api_version)
        print([node.node_id for node in nodes])


if __name__ == "__main__":
    asyncio.run(main())
```

## Documentation map

Start with `docs/api-reference.md` when you want a compact inventory of the
public client methods, exports, compatibility aliases, and construction rules.

- `docs/api-reference.md` for the central public API inventory
- `docs/cli.md` for the function probe CLI and shell examples
- `docs/config.md` for system, node, and zone config reads and writes
- `docs/live-testing.md` for local opt-in tests against a real Duco device
- `docs/replay-testing.md` for local sample validation against ignored raw API
  captures
- `docs/actions.md` for action discovery and execution
- `docs/nodes.md` for node models and node information readers
- `docs/public-api-boundaries.md` for the typed-model contract and raw escape
  hatch boundaries
- `docs/zones.md` for zone and group info and config readers
- `docs/ventilation-states.md` for ventilation enum values and compatibility
  members
- `docs/payload-preservation.md` for raw payload preservation and raw endpoint
  access

The public surface keeps a deliberate split between stable typed readers and
broader raw escape hatches. Use the typed methods when the model already
matches the data you need, and use the raw helpers when you need endpoint
coverage, selector flexibility, or payload fields that have not been typed yet.
See `docs/public-api-boundaries.md` for the full contract.

## Testing strategy

The repository uses three automated test layers:

- Synthetic unit tests cover focused parser and client behavior with mocked HTTP
  responses.
- Local sample-validation tests can replay a small set of typed client methods
  against your own ignored raw API captures.
- Live tests validate read paths, safe writes, and latency probes against your
  own Duco device.

That split matters for Duco support. Synthetic tests keep day-to-day iteration
fast. Local sample validation lets you check real captures without committing
them or maintaining a sanitization workflow. Live tests confirm that the client
still behaves correctly against actual hardware.

## Public API maintenance

The compact API reference is generated from the published exports and public
async client methods. Regenerate it after public surface changes with:

```bash
python tools/api_reference.py write
```

## Development

From the repository root, use any activated virtual environment you prefer. The
commands below use a local `.venv` so they stay copy-pasteable from a clean
checkout. Create it first if needed, then install the development dependencies
and run the same checks as CI:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/pytest
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/mypy src
.venv/bin/bandit -r src -ll
.venv/bin/pip-audit --desc on
```

For local function probes without activating the environment first:

```bash
.venv/bin/python -m duco_connectivity --host 192.168.1.10 call async_get_board_info
.venv/bin/duco-probe --host 192.168.1.10 call async_get_board_info
.venv/bin/duco-probe --host 192.168.1.10 call async_get_ventilation_temperature_info
.venv/bin/duco-probe --host 192.168.1.10 call async_get_bypass_supply_temperature_target --kwargs '{"zone_id": 1}'
```

For local real-device validation against your own Duco box, use the opt-in
workflow documented in `docs/live-testing.md`.

For local sample validation against ignored raw captures,
use `docs/replay-testing.md`.

If you want to validate raw API captures locally, follow the layout guidance in
`docs/replay-testing.md` and the fixture-specific notes in
`tests/fixtures/replay/README.md`.

## Validation

The current API surface was validated against a real Duco box during the first
development pass, covering:

- `GET /api`
- `GET /info` with generic module, submodule, and parameter queries
- `GET /config` with generic module, submodule, and parameter queries
- `PATCH /config` with a no-op `TimeZone` write against the current value
- `GET /info?module=General&submodule=Board`
- `GET /info?module=General&submodule=Lan`
- `GET /info?module=Ventilation`
- `GET /info?module=HeatRecovery`
- `GET /info/nodes`
- `GET /info?module=General&submodule=PublicApi`
- `GET /config?module=HeatRecovery&submodule=Bypass&parameter=TempSupTgtZone1`
- `PATCH /config?module=HeatRecovery&submodule=Bypass&parameter=TempSupTgtZone1` with a no-op write against the current value
- `POST /action/nodes/{node}` with a no-op `SetVentilationState`

The repository now also includes opt-in local live tests so the same read and
safe-write checks can be repeated against your own device without changing the
default mock-only test workflow.
