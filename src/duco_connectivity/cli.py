"""Function probe CLI for python-duco-connectivity."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from typing import Any

import aiohttp

from . import DucoClient, __version__
from .exceptions import DucoConnectionError, DucoError


@dataclass(frozen=True, slots=True)
class MethodSpec:
    """CLI metadata for a supported probe call."""

    parameters: tuple[str, ...] = ()
    required: tuple[str, ...] = ()
    description: str = ""


METHOD_SPECS: dict[str, MethodSpec] = {
    "async_get_api_info": MethodSpec(description="Return advertised API metadata."),
    "async_get_actions": MethodSpec(description="Return supported system actions."),
    "async_get_node_actions": MethodSpec(description="Return supported actions per node."),
    "async_get_node_actions_for_node": MethodSpec(
        parameters=("node_id",),
        required=("node_id",),
        description="Return supported actions for one node.",
    ),
    "async_get_raw": MethodSpec(
        parameters=("path", "params"),
        required=("path",),
        description="Return an unmapped raw GET response.",
    ),
    "async_get_info": MethodSpec(
        parameters=("module", "submodule", "parameter"),
        description="Return a raw response from /info.",
    ),
    "async_get_config": MethodSpec(
        parameters=("module", "submodule", "parameter"),
        description="Return a typed response from /config.",
    ),
    "async_get_node_configs_raw": MethodSpec(
        parameters=("parameter",),
        description="Return the raw response from /config/nodes.",
    ),
    "async_get_node_config_raw": MethodSpec(
        parameters=("node_id", "parameter"),
        required=("node_id",),
        description="Return the raw response from /config/nodes/{node}.",
    ),
    "async_get_node_configs": MethodSpec(
        parameters=("parameter",),
        description="Return the typed response from /config/nodes.",
    ),
    "async_get_node_config": MethodSpec(
        parameters=("node_id", "parameter"),
        required=("node_id",),
        description="Return the typed response from /config/nodes/{node}.",
    ),
    "async_get_zones_config": MethodSpec(
        parameters=("zone", "group", "module", "submodule", "parameter"),
        description="Return the typed response from /config/zones.",
    ),
    "async_get_zone_config": MethodSpec(
        parameters=("zone_id", "group", "module", "submodule", "parameter"),
        required=("zone_id",),
        description="Return the typed response from /config/zones/{zone}.",
    ),
    "async_get_board_info": MethodSpec(description="Return board identity details."),
    "async_get_lan_info": MethodSpec(description="Return LAN settings."),
    "async_get_diagnostics": MethodSpec(description="Return diagnostic subsystem states."),
    "async_get_nodes": MethodSpec(description="Return full node information."),
    "async_get_zones_info": MethodSpec(description="Return zone information."),
    "async_get_zone_info": MethodSpec(
        parameters=("zone_id", "group", "module", "submodule", "parameter"),
        required=("zone_id",),
        description="Return detailed information for one zone.",
    ),
    "async_get_zone_group_info": MethodSpec(
        parameters=("zone_id", "group_id", "module", "submodule", "parameter"),
        required=("zone_id", "group_id"),
        description="Return detailed information for one zone group.",
    ),
    "async_get_nodes_overview": MethodSpec(description="Return lightweight node identifiers."),
    "async_get_node_info": MethodSpec(
        parameters=("node_id", "module", "parameter"),
        required=("node_id",),
        description="Return detailed information for one node.",
    ),
    "async_get_write_requests_remaining": MethodSpec(
        description="Return the remaining write budget.",
    ),
    "async_get_write_req_remaining": MethodSpec(
        description="Return the backward-compatible write budget alias.",
    ),
}

PARAMETER_FLAGS = {
    "node_id": "--node-id",
    "zone_id": "--zone-id",
    "group_id": "--group-id",
    "zone": "--zone",
    "group": "--group",
    "module": "--module",
    "submodule": "--submodule",
    "parameter": "--parameter",
    "path": "--path",
    "params": "--query KEY=VALUE",
}


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        prog="duco-probe",
        description=(
            "Probe supported DucoClient read methods and print their return values as JSON."
        ),
    )
    parser.add_argument("--host", required=True, help="Duco host or IP address")
    parser.add_argument("--port", type=int, help="Optional port override")
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=10.0,
        help="Request timeout in seconds",
    )
    parser.add_argument(
        "--include-raw-payload",
        action="store_true",
        help="Include raw_payload fields in serialized output",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    call_parser = subparsers.add_parser(
        "call",
        help="Call a supported DucoClient read method",
        description="Call a supported DucoClient read method and print the JSON result.",
    )
    call_parser.add_argument(
        "method",
        choices=tuple(METHOD_SPECS),
        help="Public DucoClient read method to probe",
    )
    call_parser.add_argument("--node-id", type=int, help="Node identifier")
    call_parser.add_argument("--zone-id", type=int, help="Zone identifier")
    call_parser.add_argument("--group-id", type=int, help="Zone group identifier")
    call_parser.add_argument("--zone", type=int, help="Zone query filter")
    call_parser.add_argument("--group", type=int, help="Group query filter")
    call_parser.add_argument("--module", help="Module query argument")
    call_parser.add_argument("--submodule", help="Submodule query argument")
    call_parser.add_argument("--parameter", help="Parameter query argument")
    call_parser.add_argument("--path", help="API-relative path for async_get_raw")
    call_parser.add_argument(
        "--query",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Repeatable raw query argument for async_get_raw",
    )

    return parser


def _parse_query_items(query_items: Sequence[str]) -> dict[str, str]:
    """Parse repeated KEY=VALUE query items."""
    params: dict[str, str] = {}

    for item in query_items:
        key, separator, value = item.partition("=")
        if separator != "=" or not key:
            msg = f"Invalid query item: {item}. Use KEY=VALUE."
            raise ValueError(msg)
        if key in params:
            msg = f"Duplicate query key: {key}"
            raise ValueError(msg)
        params[key] = value

    return params


def _build_method_kwargs(args: argparse.Namespace, spec: MethodSpec) -> dict[str, Any]:
    """Build keyword arguments for a supported method call."""
    kwargs: dict[str, Any] = {}

    for parameter, flag in PARAMETER_FLAGS.items():
        if parameter == "params":
            if args.query and parameter not in spec.parameters:
                msg = f"{args.method} does not support {flag}"
                raise ValueError(msg)
            if parameter in spec.parameters:
                parsed_params = _parse_query_items(args.query)
                if parsed_params:
                    kwargs[parameter] = parsed_params
            continue

        value = getattr(args, parameter)
        if value is None:
            if parameter in spec.required:
                msg = f"{args.method} requires {flag}"
                raise ValueError(msg)
            continue

        if parameter not in spec.parameters:
            msg = f"{args.method} does not support {flag}"
            raise ValueError(msg)

        kwargs[parameter] = value

    return kwargs


def _serialize_value(value: Any, *, include_raw_payload: bool) -> Any:
    """Convert a result into JSON-serializable data."""
    if is_dataclass(value):
        data: dict[str, Any] = {}
        for field in fields(value):
            if field.name == "raw_payload" and not include_raw_payload:
                continue
            data[field.name] = _serialize_value(
                getattr(value, field.name),
                include_raw_payload=include_raw_payload,
            )
        return data

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, dict):
        return {
            key: _serialize_value(item, include_raw_payload=include_raw_payload)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_serialize_value(item, include_raw_payload=include_raw_payload) for item in value]

    return value


async def _async_call(args: argparse.Namespace) -> Any:
    """Execute a supported probe call."""
    spec = METHOD_SPECS[args.method]
    kwargs = _build_method_kwargs(args, spec)

    async with aiohttp.ClientSession() as session:
        client = DucoClient(
            session=session,
            host=args.host,
            port=args.port,
            request_timeout=args.request_timeout,
        )
        method = getattr(client, args.method)
        return await method(**kwargs)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the function probe CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = asyncio.run(_async_call(args))
    except ValueError as err:
        print(str(err), file=sys.stderr)
        return 2
    except (DucoConnectionError, DucoError) as err:
        print(str(err), file=sys.stderr)
        return 1

    serialized = _serialize_value(result, include_raw_payload=args.include_raw_payload)
    print(json.dumps(serialized, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
