"""Sanitize raw replay fixtures into publishable replay profiles."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from ipaddress import ip_address
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "replay"
RAW_REPLAY_FIXTURE_ROOT = REPLAY_FIXTURE_ROOT / "raw"
SANITIZED_REPLAY_FIXTURE_ROOT = REPLAY_FIXTURE_ROOT / "sanitized"

PRESERVED_KEYS = {
    "apiversion",
    "boxname",
    "boxsubtypename",
    "component",
    "publicapiversion",
    "status",
}
VALUE_WRAPPER_KEYS = {"inc", "max", "min", "options", "val"}
IP_KEYS = {
    "defaultgateway",
    "dns",
    "ducoclientip",
    "ip",
    "staticdefaultgateway",
    "staticdns",
    "staticip",
}
HOSTNAME_KEYS = {"hostname"}
MAC_KEYS = {"bssid", "mac"}
SECRET_KEYS = {"key", "passphrase", "password", "wifiapkey"}
NAME_KEYS = {"name"}
SSID_KEYS = {"ssid", "wificlientssid", "wifiapssid"}
SERIAL_FRAGMENT = "serial"
MAC_RE = re.compile(r"^(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")
FLAT_EXPORT_SUFFIX_TO_PATH = {
    "api": PurePosixPath("GET/api/__base__.json"),
    "config": PurePosixPath("GET/config/__base__.json"),
    "config_nodes": PurePosixPath("GET/config/nodes/__base__.json"),
    "config_zones": PurePosixPath("GET/config/zones/__base__.json"),
    "info": PurePosixPath("GET/info/__base__.json"),
    "info_nodes": PurePosixPath("GET/info/nodes/__base__.json"),
    "info_zones": PurePosixPath("GET/info/zones/__base__.json"),
}


def sanitize_replay_profile(
    profile: str,
    *,
    raw_profile: str | None = None,
    raw_root: Path = RAW_REPLAY_FIXTURE_ROOT,
    sanitized_root: Path = SANITIZED_REPLAY_FIXTURE_ROOT,
) -> list[Path]:
    """Sanitize every raw replay fixture for a profile."""
    raw_profile_root = raw_root / (raw_profile or profile)
    if not raw_profile_root.is_dir():
        missing_profile = raw_profile or profile
        raise FileNotFoundError(
            f"No raw replay fixture profile found for {missing_profile} at "
            f"{raw_profile_root}"
        )

    raw_files = sorted(raw_profile_root.rglob("*.json"))
    if not raw_files:
        raise FileNotFoundError(
            f"No raw replay fixture files found for {profile} at {raw_profile_root}"
        )

    sanitizer = ReplaySanitizer()
    written_paths: list[Path] = []

    for raw_file in raw_files:
        relative_path = raw_file.relative_to(raw_profile_root)
        normalized_relative_path = _normalize_raw_fixture_relative_path(relative_path)
        payload = json.loads(raw_file.read_text(encoding="utf-8"))
        sanitized_payload = sanitizer.sanitize(payload)
        output_path = sanitized_root / profile / normalized_relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(sanitized_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        written_paths.append(output_path)

    return written_paths


@dataclass(slots=True)
class ReplaySanitizer:
    """Sanitize installation-specific values while preserving API structure."""

    _replacement_counters: dict[str, int] = field(default_factory=dict)
    _replacement_maps: dict[str, dict[str, str]] = field(default_factory=dict)

    def sanitize(self, payload: object) -> object:
        """Return a sanitized copy of a JSON-compatible payload."""
        return self._sanitize_value(payload, path=())

    def _sanitize_value(self, value: object, *, path: tuple[str, ...]) -> object:
        if isinstance(value, dict):
            return {
                key: self._sanitize_value(item, path=path + (str(key),))
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self._sanitize_value(item, path=path) for item in value]
        if isinstance(value, str):
            return self._sanitize_string(value, path=path)
        return value

    def _sanitize_string(self, value: str, *, path: tuple[str, ...]) -> str:
        if not value:
            return value

        category = _categorize_sensitive_string(value, path=path)
        if category is None:
            return value

        return self._replacement_for(category, value)

    def _replacement_for(self, category: str, original: str) -> str:
        category_map = self._replacement_maps.setdefault(category, {})
        if original in category_map:
            return category_map[original]

        replacement_index = self._replacement_counters.get(category, 0) + 1
        self._replacement_counters[category] = replacement_index
        replacement = _build_replacement(category, replacement_index)
        category_map[original] = replacement
        return replacement


def _normalize_raw_fixture_relative_path(relative_path: Path) -> Path:
    if len(relative_path.parts) == 1:
        return _normalize_flat_raw_export_path(relative_path.name)

    if len(relative_path.parts) < 3:
        raise ValueError(
            "raw replay fixtures must include method, endpoint path, and file name"
        )
    if relative_path.suffix != ".json":
        raise ValueError(f"unsupported raw replay fixture file type: {relative_path.name}")

    method = relative_path.parts[0].upper()
    return Path(method, *relative_path.parts[1:])


def _normalize_flat_raw_export_path(file_name: str) -> Path:
    if not file_name.endswith(".json"):
        raise ValueError(f"unsupported raw replay fixture file type: {file_name}")

    stem = file_name[:-5]
    prefix, separator, suffix = stem.partition("_")
    if not separator or not prefix or not suffix:
        raise ValueError(
            "flat raw replay exports must use '<PROFILE>_<endpoint>.json' names"
        )

    normalized_suffix = suffix.lower()
    mapped_path = FLAT_EXPORT_SUFFIX_TO_PATH.get(normalized_suffix)
    if mapped_path is None:
        known_suffixes = ", ".join(sorted(FLAT_EXPORT_SUFFIX_TO_PATH))
        raise ValueError(
            f"unsupported flat raw replay export suffix {suffix!r}; expected "
            f"one of: {known_suffixes}"
        )

    return Path(*mapped_path.parts)


def _categorize_sensitive_string(value: str, *, path: tuple[str, ...]) -> str | None:
    normalized_key = _normalized_path_key(path)
    if normalized_key in PRESERVED_KEYS:
        return None

    if value == "0.0.0.0":
        return None

    if normalized_key in MAC_KEYS or MAC_RE.fullmatch(value):
        return "mac"

    ip_category = _ip_replacement_category(value)
    if normalized_key in IP_KEYS and ip_category is not None:
        return ip_category

    if SERIAL_FRAGMENT in normalized_key:
        return "serial"
    if normalized_key in HOSTNAME_KEYS:
        return "hostname"
    if normalized_key in NAME_KEYS:
        return "name"
    if normalized_key in SSID_KEYS or "ssid" in normalized_key:
        return "ssid"
    if normalized_key in SECRET_KEYS or normalized_key.endswith("key"):
        return "secret"

    return None


def _normalized_path_key(path: tuple[str, ...]) -> str:
    for key in reversed(path):
        normalized_key = re.sub(r"[^a-z0-9]", "", key.lower())
        if normalized_key and normalized_key not in VALUE_WRAPPER_KEYS:
            return normalized_key

    return ""


def _ip_replacement_category(value: str) -> str | None:
    try:
        parsed = ip_address(value)
    except ValueError:
        return None

    if parsed.version == 4:
        return "ipv4"
    return "ipv6"


def _build_replacement(category: str, replacement_index: int) -> str:
    if category == "ipv4":
        if replacement_index > 254:
            raise ValueError("too many IPv4 replacements for TEST-NET-1")
        return f"192.0.2.{replacement_index}"

    if category == "ipv6":
        return f"2001:db8::{replacement_index}"

    if category == "mac":
        if replacement_index > 255:
            raise ValueError("too many MAC replacements for placeholder range")
        return f"02:00:00:00:00:{replacement_index:02x}"

    return f"sanitized-{category}-{replacement_index}"


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sanitize raw replay fixtures into a publishable profile"
    )
    parser.add_argument("profile", help="Replay profile slug to sanitize")
    parser.add_argument(
        "--raw-profile",
        help="Optional source directory name below tests/fixtures/replay/raw/",
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=RAW_REPLAY_FIXTURE_ROOT,
        help="Root directory containing raw replay fixture profiles",
    )
    parser.add_argument(
        "--sanitized-root",
        type=Path,
        default=SANITIZED_REPLAY_FIXTURE_ROOT,
        help="Root directory where sanitized replay profiles are written",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    """Run the raw-to-sanitized replay fixture conversion."""
    args = _parse_args(argv)
    written_paths = sanitize_replay_profile(
        args.profile,
        raw_profile=args.raw_profile,
        raw_root=args.raw_root,
        sanitized_root=args.sanitized_root,
    )

    print(
        f"Sanitized {len(written_paths)} replay fixture(s) into "
        f"{args.sanitized_root / args.profile}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())