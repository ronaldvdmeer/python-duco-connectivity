"""Generate the API reference page for the public library surface."""

from __future__ import annotations

import argparse
import inspect
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import duco_connectivity  # noqa: E402
from duco_connectivity import DucoClient  # noqa: E402

DOC_PATH = ROOT / "docs" / "api-reference.md"


@dataclass(frozen=True)
class MethodMetadata:
    """Additional method metadata used to render the API reference."""

    category: str
    endpoint: str
    surface: str
    details_path: str | None = None
    notes: tuple[str, ...] = ()


CATEGORY_ORDER = [
    "Core access",
    "Actions and commands",
    "Node configuration",
    "Zone information and configuration",
    "Node and system information",
    "Compatibility methods",
]


METHOD_METADATA: dict[str, MethodMetadata] = {
    "async_get_api_info": MethodMetadata(
        category="Core access",
        endpoint="GET /api",
        surface="typed",
    ),
    "async_get_raw": MethodMetadata(
        category="Core access",
        endpoint="GET <api-relative path>",
        surface="raw escape hatch",
        details_path="payload-preservation.md",
        notes=(
            "Use API-relative paths like `/info/nodes/7` and pass query arguments via `params`.",
        ),
    ),
    "async_get_info": MethodMetadata(
        category="Core access",
        endpoint="GET /info",
        surface="raw escape hatch",
        details_path="payload-preservation.md",
    ),
    "async_get_config": MethodMetadata(
        category="Core access",
        endpoint="GET /config",
        surface="typed",
        details_path="config.md",
    ),
    "async_set_config": MethodMetadata(
        category="Core access",
        endpoint="PATCH /config",
        surface="typed",
        details_path="config.md",
        notes=(
            "Accepts sparse payloads built from `PatchConfigValue(...)` leaves or raw "
            "API-shaped `{'Val': ...}` objects.",
        ),
    ),
    "async_get_actions": MethodMetadata(
        category="Actions and commands",
        endpoint="GET /action",
        surface="typed",
        details_path="actions.md",
    ),
    "async_get_node_actions": MethodMetadata(
        category="Actions and commands",
        endpoint="GET /action/nodes",
        surface="typed",
        details_path="actions.md",
    ),
    "async_get_node_actions_for_node": MethodMetadata(
        category="Actions and commands",
        endpoint="GET /action/nodes/{node}",
        surface="typed",
        details_path="actions.md",
    ),
    "async_set_action": MethodMetadata(
        category="Actions and commands",
        endpoint="POST /action",
        surface="typed",
        details_path="actions.md",
    ),
    "async_set_ventilation_state": MethodMetadata(
        category="Actions and commands",
        endpoint="POST /action/nodes/{node}",
        surface="wrapper",
        details_path="actions.md",
        notes=(
            "Thin convenience wrapper over `async_set_node_action()` for `SetVentilationState`.",
        ),
    ),
    "async_set_node_action": MethodMetadata(
        category="Actions and commands",
        endpoint="POST /action/nodes/{node}",
        surface="typed",
        details_path="actions.md",
    ),
    "async_get_node_configs_raw": MethodMetadata(
        category="Node configuration",
        endpoint="GET /config/nodes",
        surface="raw escape hatch",
        details_path="config.md",
    ),
    "async_get_node_config_raw": MethodMetadata(
        category="Node configuration",
        endpoint="GET /config/nodes/{node}",
        surface="raw escape hatch",
        details_path="config.md",
    ),
    "async_set_node_config_raw": MethodMetadata(
        category="Node configuration",
        endpoint="PATCH /config/nodes/{node}",
        surface="raw escape hatch",
        details_path="config.md",
        notes=("May return `None` when the box acknowledges the write without a JSON body.",),
    ),
    "async_get_node_configs": MethodMetadata(
        category="Node configuration",
        endpoint="GET /config/nodes",
        surface="typed",
        details_path="config.md",
        notes=("The typed reader currently supports only `parameter='Name'`.",),
    ),
    "async_get_node_config": MethodMetadata(
        category="Node configuration",
        endpoint="GET /config/nodes/{node}",
        surface="typed",
        details_path="config.md",
        notes=("The typed reader currently supports only `parameter='Name'`.",),
    ),
    "async_set_node_config": MethodMetadata(
        category="Node configuration",
        endpoint="PATCH /config/nodes/{node}",
        surface="typed",
        details_path="config.md",
        notes=(
            "The typed writer always targets `parameter='Name'` so it can return a stable "
            "`ConfigNode`.",
        ),
    ),
    "async_get_zones_config": MethodMetadata(
        category="Zone information and configuration",
        endpoint="GET /config/zones",
        surface="typed",
        details_path="zones.md",
    ),
    "async_get_zone_config": MethodMetadata(
        category="Zone information and configuration",
        endpoint="GET /config/zones/{zone}",
        surface="typed",
        details_path="zones.md",
    ),
    "async_set_zone_config": MethodMetadata(
        category="Zone information and configuration",
        endpoint="PATCH /config/zones/{zone}",
        surface="typed",
        details_path="zones.md",
        notes=(
            "Accepts sparse payloads built from `PatchConfigValue(...)` leaves or raw "
            "API-shaped `{'Val': ...}` objects.",
        ),
    ),
    "async_get_zones_info": MethodMetadata(
        category="Zone information and configuration",
        endpoint="GET /info/zones",
        surface="typed",
        details_path="zones.md",
    ),
    "async_get_zone_info": MethodMetadata(
        category="Zone information and configuration",
        endpoint="GET /info/zones/{zone}",
        surface="typed",
        details_path="zones.md",
    ),
    "async_get_zone_group_info": MethodMetadata(
        category="Zone information and configuration",
        endpoint="GET /info/zones/{zone}/groups/{group}",
        surface="typed",
        details_path="zones.md",
    ),
    "async_get_board_info": MethodMetadata(
        category="Node and system information",
        endpoint="GET /info?module=General&submodule=Board",
        surface="typed",
    ),
    "async_get_lan_info": MethodMetadata(
        category="Node and system information",
        endpoint="GET /info?module=General&submodule=Lan",
        surface="typed",
    ),
    "async_get_diagnostics": MethodMetadata(
        category="Node and system information",
        endpoint="GET /info?module=Diag",
        surface="typed",
    ),
    "async_get_nodes": MethodMetadata(
        category="Node and system information",
        endpoint="GET /info/nodes",
        surface="typed",
        details_path="nodes.md",
    ),
    "async_get_nodes_overview": MethodMetadata(
        category="Node and system information",
        endpoint="GET /nodes",
        surface="typed",
        details_path="nodes.md",
    ),
    "async_get_node_info": MethodMetadata(
        category="Node and system information",
        endpoint="GET /info/nodes/{node}",
        surface="typed",
        details_path="nodes.md",
    ),
    "async_get_write_requests_remaining": MethodMetadata(
        category="Node and system information",
        endpoint="GET /info?module=General&submodule=PublicApi",
        surface="typed",
    ),
    "async_get_write_req_remaining": MethodMetadata(
        category="Compatibility methods",
        endpoint="Alias of async_get_write_requests_remaining()",
        surface="compatibility alias",
        notes=("Kept for callers still using the previous `python-duco-client` method name.",),
    ),
}


COMPATIBILITY_EXPORTS = {
    "ApiEndpointInfo",
    "DucoRateLimitError",
}


COMPATIBILITY_NOTES = (
    "`async_get_write_req_remaining()` delegates to `async_get_write_requests_remaining()`.",
    "`DucoRateLimitError` is a backward-compatible alias of `DucoWriteLimitError`.",
    "`ApiEndpointInfo` is a backward-compatible alias of `ApiEndpoint`.",
    "`ApiInfo(api_version=...)` and `ApiInfo.api_version` remain available for migration "
    "compatibility while the public field name is `public_api_version`.",
)


SEE_ALSO = (
    ("config.md", "System, node, and zone config reads and writes"),
    ("actions.md", "System and node action discovery and execution"),
    ("nodes.md", "Node models and node information readers"),
    ("zones.md", "Zone and group info and config models"),
    ("ventilation-states.md", "Ventilation enums and compatibility values"),
    ("payload-preservation.md", "Raw payload preservation and raw endpoint access"),
)


@dataclass(frozen=True)
class MethodReference:
    """Rendered method information for the API reference."""

    name: str
    signature: str
    summary: str
    metadata: MethodMetadata


def _format_annotation(annotation: object) -> str:
    """Format a signature annotation for Markdown output."""
    return (
        inspect.formatannotation(annotation)
        .replace("typing.", "")
        .replace("duco_connectivity.models.", "")
        .replace("aiohttp.client.", "")
    )


def _format_signature(method: object, name: str) -> str:
    """Return a readable public method signature without the `self` parameter."""
    signature = str(inspect.signature(method))
    signature = signature.replace("(self, ", "(")
    signature = signature.replace("(self)", "()")
    signature = signature.replace("typing.", "")
    signature = signature.replace("duco_connectivity.models.", "")
    signature = signature.replace("aiohttp.client.", "")
    return f"{name}{signature}"


def collect_method_references() -> dict[str, list[MethodReference]]:
    """Collect public client methods grouped by documentation category."""
    public_methods = [
        (name, member)
        for name, member in DucoClient.__dict__.items()
        if name.startswith(("async_get_", "async_set_")) and inspect.iscoroutinefunction(member)
    ]

    public_names = {name for name, _member in public_methods}
    metadata_names = set(METHOD_METADATA)
    if public_names != metadata_names:
        missing = sorted(public_names - metadata_names)
        extra = sorted(metadata_names - public_names)
        details: list[str] = []
        if missing:
            details.append(f"missing metadata for: {', '.join(missing)}")
        if extra:
            details.append(f"metadata without method: {', '.join(extra)}")
        raise ValueError("Method metadata mismatch: " + "; ".join(details))

    references = {category: [] for category in CATEGORY_ORDER}
    for name, member in public_methods:
        summary = inspect.getdoc(member)
        if summary is None:
            raise ValueError(f"Missing docstring for public method {name}")

        references[METHOD_METADATA[name].category].append(
            MethodReference(
                name=name,
                signature=_format_signature(member, name),
                summary=summary.splitlines()[0],
                metadata=METHOD_METADATA[name],
            )
        )

    return references


def collect_public_symbols() -> dict[str, list[str]]:
    """Group public exports into scan-friendly sections."""
    groups = {
        "Client": [],
        "Models": [],
        "Enums": [],
        "Exceptions": [],
        "Other": [],
    }

    for name in duco_connectivity.__all__:
        if name in COMPATIBILITY_EXPORTS:
            continue
        if name == "DucoClient":
            groups["Client"].append(name)
            continue
        if name == "__version__":
            groups["Other"].append(name)
            continue

        value = getattr(duco_connectivity, name)
        if inspect.isclass(value):
            if issubclass(value, Exception):
                groups["Exceptions"].append(name)
            elif issubclass(value, Enum):
                groups["Enums"].append(name)
            else:
                groups["Models"].append(name)
            continue

        groups["Models"].append(name)

    for group in groups.values():
        group.sort()

    covered = set().union(*groups.values(), COMPATIBILITY_EXPORTS)
    if covered != set(duco_connectivity.__all__):
        missing = sorted(set(duco_connectivity.__all__) - covered)
        raise ValueError(f"Uncovered public exports: {', '.join(missing)}")

    return groups


def render_api_reference() -> str:
    """Render the full API reference Markdown page."""
    references = collect_method_references()
    symbols = collect_public_symbols()
    constructor_signature = _format_signature(DucoClient.__init__, "DucoClient")

    lines = [
        "# API reference",
        "",
        "This page is the compact inventory for the public `python-duco-connectivity` surface.",
        "It is generated from the public exports in `src/duco_connectivity/__init__.py`",
        "and the public async methods on `DucoClient`.",
        "",
        "Regenerate it after public surface changes with:",
        "",
        "```bash",
        "python tools/api_reference.py write",
        "```",
        "",
        "## Navigation",
        "",
        "- Start with the client construction rules if you need connection setup behavior.",
        "- Use the method groups below to find the right entry point quickly.",
        "- Use the topic links at the bottom when you need deeper examples or model detail.",
        "",
        "## Client construction",
        "",
        f"- `{constructor_signature}`",
        "- HTTP only: HTTPS is rejected intentionally.",
        "- `host` must not include credentials, a path, a query string, or a fragment.",
        "- Embedded host ports are allowed, but you cannot specify a port both inside "
        "`host` and via `port=`.",
        "- Unbracketed IPv6 host values are rejected; use `[addr]` or `[addr]:port`.",
        "- Invalid host input raises `ValueError` before any request is attempted.",
        "- Request transport failures raise `DucoConnectionError`.",
        "- HTTP error responses raise `DucoError`.",
        "- Write-budget exhaustion raises `DucoWriteLimitError`.",
        "",
        "## Client methods",
        "",
    ]

    for category in CATEGORY_ORDER:
        methods = references[category]
        if not methods:
            continue
        lines.append(f"### {category}")
        lines.append("")
        for reference in methods:
            lines.append(f"- `{reference.signature}`")
            lines.append(f"  - Endpoint: `{reference.metadata.endpoint}`")
            lines.append(f"  - Surface: {reference.metadata.surface}")
            lines.append(f"  - Summary: {reference.summary}")
            if reference.metadata.details_path is not None:
                lines.append(
                    "  - Details: "
                    f"[{reference.metadata.details_path}]({reference.metadata.details_path})"
                )
            for note in reference.metadata.notes:
                lines.append(f"  - Note: {note}")
        lines.append("")

    lines.extend(
        [
            "## Public exports",
            "",
            "The package exports the following public symbols through `duco_connectivity.__all__`.",
            "",
        ]
    )

    for label in ("Client", "Models", "Enums", "Exceptions", "Other"):
        names = symbols[label]
        if not names:
            continue
        lines.append(f"### {label}")
        lines.append("")
        for name in names:
            lines.append(f"- `{name}`")
        lines.append("")

    lines.extend(
        [
            "## Compatibility details",
            "",
        ]
    )
    for note in COMPATIBILITY_NOTES:
        lines.append(f"- {note}")
    lines.append("")

    lines.extend(
        [
            "## See also",
            "",
        ]
    )
    for path, description in SEE_ALSO:
        lines.append(f"- [{path}]({path}) for {description}")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    """Run the API reference helper."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("write", "check", "print"),
        nargs="?",
        default="print",
        help="Write the reference file, verify it is current, or print it to stdout.",
    )
    args = parser.parse_args()

    rendered = render_api_reference()
    if args.command == "print":
        print(rendered)
        return 0

    if args.command == "write":
        DOC_PATH.write_text(rendered, encoding="utf-8")
        print(f"Wrote {DOC_PATH.relative_to(ROOT)}")
        return 0

    current = DOC_PATH.read_text(encoding="utf-8")
    if current != rendered:
        print("docs/api-reference.md is out of date", file=sys.stderr)
        return 1

    print("docs/api-reference.md is up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
