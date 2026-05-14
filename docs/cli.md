# CLI probe

`python-duco-connectivity` now includes a small probe CLI for inspecting the
return value of supported public `DucoClient` read methods against a local Duco
box.

The CLI is meant for library validation and integration development. Use it
when you want to call the same library method that Home Assistant or another
consumer will call and inspect the exact JSON-serialized result.

## Entry points

After installation, you can use either entry point. When you are not inside an
activated virtual environment, prefer the explicit `.venv/bin/...` paths:

```bash
.venv/bin/duco-probe --host 192.168.1.10 call async_get_board_info
.venv/bin/python -m duco_connectivity --host 192.168.1.10 call async_get_board_info
```

Both entry points run the same code path and print JSON to stdout.

If you activate the environment first, the shorter commands work too:

```bash
source .venv/bin/activate
duco-probe --host 192.168.1.10 call async_get_board_info
python -m duco_connectivity --host 192.168.1.10 call async_get_board_info
```

## Output behavior

- Output is JSON by default
- Dataclasses, enums, lists, tuples, and dicts are serialized recursively
- `raw_payload` fields are omitted by default to keep the output focused
- Pass `--include-raw-payload` when you want the preserved API-shaped payloads

Example:

```bash
.venv/bin/duco-probe --host 192.168.1.10 --include-raw-payload call async_get_board_info
```

## Supported read methods

The first probe-focused release supports the public read methods that are most
useful when validating the Home Assistant integration and nearby library use
cases:

- `async_get_api_info`
- `async_get_actions`
- `async_get_node_actions`
- `async_get_node_actions_for_node`
- `async_get_raw`
- `async_get_info`
- `async_get_config`
- `async_get_node_configs_raw`
- `async_get_node_config_raw`
- `async_get_node_configs`
- `async_get_node_config`
- `async_get_zones_config`
- `async_get_zone_config`
- `async_get_board_info`
- `async_get_lan_info`
- `async_get_diagnostics`
- `async_get_nodes`
- `async_get_zones_info`
- `async_get_zone_info`
- `async_get_zone_group_info`
- `async_get_nodes_overview`
- `async_get_node_info`
- `async_get_write_requests_remaining`

Write methods are intentionally out of scope for the first CLI iteration.

## Common examples

Board info probe:

```bash
.venv/bin/duco-probe --host 192.168.1.10 call async_get_board_info
```

LAN info probe:

```bash
.venv/bin/duco-probe --host 192.168.1.10 call async_get_lan_info
```

Detailed node probe:

```bash
.venv/bin/duco-probe --host 192.168.1.10 call async_get_node_info --node-id 7
```

Zone info probe with filters:

```bash
.venv/bin/duco-probe \
  --host 192.168.1.10 \
  call async_get_zone_info \
  --zone-id 1 \
  --group 1 \
  --module General
```

Raw `/info` probe that mirrors the board info query:

```bash
.venv/bin/duco-probe \
  --host 192.168.1.10 \
  call async_get_raw \
  --path /info \
  --query module=General \
  --query submodule=Board
```

## Method argument mapping

The CLI intentionally mirrors the Python method parameters instead of adding a
second abstraction layer.

Examples:

- `--node-id` maps to `node_id`
- `--zone-id` maps to `zone_id`
- `--group-id` maps to `group_id`
- `--module`, `--submodule`, and `--parameter` map directly to the same named
  Python keyword arguments
- `--query KEY=VALUE` maps to the `params` dict for `async_get_raw`

Unsupported flags for a chosen method fail fast so that probe calls stay close
to the actual library contract.

## Home Assistant validation workflow

When you want to validate a method for the Home Assistant Duco integration:

1. Identify the library method used by the integration.
2. Run the same method through `duco-probe` against a local box.
3. Inspect the JSON output for the fields the integration reads.
4. If needed, rerun with `--include-raw-payload` to compare the typed model
   with the original API-shaped data.

This CLI helps inspect library return values. It does not simulate Home
Assistant coordinators, entities, or config entry behavior.
