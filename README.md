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
- preserved `raw_payload` data on typed response models for forward compatibility

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
- `docs/config.md` for system, node, and zone config reads and writes
- `docs/actions.md` for action discovery and execution
- `docs/nodes.md` for node models and node information readers
- `docs/zones.md` for zone and group info and config readers
- `docs/ventilation-states.md` for ventilation enum values and compatibility
  members
- `docs/payload-preservation.md` for raw payload preservation and raw endpoint
  access

The public surface keeps a split between stable typed readers and broader raw
escape hatches. Use the typed methods when the model already matches the data
you need, and use the raw helpers when you need endpoint coverage that has not
been typed yet.

## Public API maintenance

The compact API reference is generated from the published exports and public
async client methods. Regenerate it after public surface changes with:

```bash
python tools/api_reference.py write
```

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
