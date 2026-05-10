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

## Public API surface

The current client exposes:

- `async_get_api_info()` for `GET /api`
- `async_get_info()` for generic `GET /info` access with optional `module`, `submodule`, and `parameter` query arguments
- `async_get_config()` for generic `GET /config` access with optional `module`, `submodule`, and `parameter` query arguments
- `async_get_board_info()` for `GET /info?module=General&submodule=Board`
- `async_get_lan_info()` for `GET /info?module=General&submodule=Lan`
- `async_get_nodes()` for `GET /info/nodes`
- `async_get_diagnostics()` for `GET /info?module=Diag`
- `async_get_write_requests_remaining()` for `GET /info?module=General&submodule=PublicApi`
- `async_set_ventilation_state()` for `POST /action/nodes/{node}` with `SetVentilationState`

The focused convenience readers remain available for the payloads that the
library already models explicitly.

The model layer includes `ApiInfo`, `BoardInfo`, `Config`, `ConfigSection`,
`ConfigValue`, `ConfigValueString`, `LanInfo`, `Node`, `NodeGeneralInfo`,
`NodeVentilationInfo`, and `NodeSensorInfo`.
The typed enum layer keeps `NodeType` closely aligned with the Duco public API
notes while preserving `UNKNOWN` as a fallback for future unmapped values.

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
- `GET /info?module=General&submodule=Board`
- `GET /info?module=General&submodule=Lan`
- `GET /info/nodes`
- `GET /info?module=General&submodule=PublicApi`
- `POST /action/nodes/{node}` with a no-op `SetVentilationState`

