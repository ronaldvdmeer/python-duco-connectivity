"""Helpers for loading local replay sample fixtures in tests."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parents[2]
REPLAY_FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "replay"
LOCAL_SAMPLE_FIXTURE_ROOT = REPLAY_FIXTURE_ROOT / "raw"
BASE_FIXTURE_NAME = "__base__.json"
QUERY_PAIR_DELIMITER = ";"
PROFILE_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True, slots=True, order=True)
class ReplayRequest:
    """Normalized request key for a stored replay fixture."""

    method: str
    path: str
    params: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class ReplayFixture:
    """Stored local replay sample payload."""

    request: ReplayRequest
    file_path: Path
    payload: object


def available_local_sample_profiles(*, root: Path = LOCAL_SAMPLE_FIXTURE_ROOT) -> tuple[str, ...]:
    """Return the available local replay sample profiles."""
    if not root.is_dir():
        return ()

    return tuple(sorted(entry.name for entry in root.iterdir() if entry.is_dir()))


def build_replay_request(
    method: str,
    path: str,
    *,
    params: Mapping[str, object] | None = None,
) -> ReplayRequest:
    """Build a normalized replay request key."""
    normalized_path, _ = _normalize_path(path)
    return ReplayRequest(
        method=_normalize_method(method),
        path=normalized_path,
        params=_normalize_params(params),
    )


def build_local_sample_fixture_path(
    profile: str,
    method: str,
    path: str,
    *,
    params: Mapping[str, object] | None = None,
    root: Path = LOCAL_SAMPLE_FIXTURE_ROOT,
) -> Path:
    """Return the deterministic path for a local replay sample fixture."""
    normalized_profile = _normalize_profile(profile)
    normalized_path, endpoint_parts = _normalize_path(path)
    request = ReplayRequest(
        method=_normalize_method(method),
        path=normalized_path,
        params=_normalize_params(params),
    )

    return root.joinpath(
        normalized_profile,
        request.method,
        *endpoint_parts,
        _fixture_file_name(request.params),
    )


def load_local_sample_fixture(
    profile: str,
    method: str,
    path: str,
    *,
    params: Mapping[str, object] | None = None,
    root: Path = LOCAL_SAMPLE_FIXTURE_ROOT,
) -> ReplayFixture:
    """Load a single local replay sample fixture from disk."""
    request = build_replay_request(method, path, params=params)
    fixture_path = build_local_sample_fixture_path(
        profile,
        method,
        path,
        params=params,
        root=root,
    )

    if not fixture_path.is_file():
        raise FileNotFoundError(
            f"No local sample fixture found for {_format_request(request)} at {fixture_path}"
        )

    return ReplayFixture(
        request=request,
        file_path=fixture_path,
        payload=json.loads(fixture_path.read_text(encoding="utf-8")),
    )


def load_local_sample_fixture_set(
    profile: str,
    *,
    root: Path = LOCAL_SAMPLE_FIXTURE_ROOT,
) -> dict[ReplayRequest, ReplayFixture]:
    """Load all local replay sample fixtures for a profile."""
    normalized_profile = _normalize_profile(profile)
    profile_root = root / normalized_profile

    if not profile_root.is_dir():
        raise FileNotFoundError(
            f"No local sample fixture profile found for {normalized_profile} at {profile_root}"
        )

    fixtures: dict[ReplayRequest, ReplayFixture] = {}

    for file_path in sorted(profile_root.rglob("*.json")):
        request = _request_from_fixture_path(file_path.relative_to(profile_root))
        if request in fixtures:
            existing_file_path = fixtures[request].file_path
            raise ValueError(
                "Duplicate local sample fixture for "
                f"{_format_request(request)}: {existing_file_path} conflicts with {file_path}"
            )

        fixtures[request] = ReplayFixture(
            request=request,
            file_path=file_path,
            payload=json.loads(file_path.read_text(encoding="utf-8")),
        )

    return fixtures


def _normalize_profile(profile: str) -> str:
    profile = profile.strip()
    if not profile:
        raise ValueError("profile must not be empty")
    if profile in {".", ".."}:
        raise ValueError("profile must not be . or ..")
    if "/" in profile or "\\" in profile:
        raise ValueError("profile must be a simple directory name")
    if Path(profile).name != profile:
        raise ValueError("profile must be a simple directory name")
    if not PROFILE_SLUG_RE.fullmatch(profile):
        raise ValueError(
            "profile must use a portable slug with lowercase letters, numbers, and hyphens"
        )
    return profile


def _normalize_method(method: str) -> str:
    method = method.strip().upper()
    if not method:
        raise ValueError("method must not be empty")
    return method


def _normalize_path(path: str) -> tuple[str, tuple[str, ...]]:
    if not path.startswith("/"):
        raise ValueError("path must start with /")
    if path.startswith("//"):
        raise ValueError("path must not start with //")
    if "\\" in path:
        raise ValueError("path must use / separators only")
    if "://" in path:
        raise ValueError("path must be API-relative, not a full URL")
    if "?" in path or "#" in path:
        raise ValueError("path must not include a query string or fragment")

    pure_path = PurePosixPath(path)
    if ".." in pure_path.parts:
        raise ValueError("path must not include parent directory traversal")

    endpoint_parts = tuple(part for part in pure_path.parts if part not in ("/", ""))
    if not endpoint_parts:
        raise ValueError("path must target an endpoint beneath /")

    return "/" + "/".join(endpoint_parts), endpoint_parts


def _normalize_params(
    params: Mapping[str, object] | None,
) -> tuple[tuple[str, str], ...]:
    if not params:
        return ()

    normalized_params: list[tuple[str, str]] = []
    for key, value in params.items():
        normalized_key = str(key)
        if not normalized_key:
            raise ValueError("params keys must not be empty")
        if value is None:
            raise ValueError(f"params[{normalized_key!r}] must not be None")
        normalized_params.append((normalized_key, str(value)))

    return tuple(sorted(normalized_params))


def _fixture_file_name(params: tuple[tuple[str, str], ...]) -> str:
    if not params:
        return BASE_FIXTURE_NAME

    encoded_params = QUERY_PAIR_DELIMITER.join(
        f"{quote(key, safe='')}={quote(value, safe='')}" for key, value in params
    )
    return f"{encoded_params}.json"


def _format_request(request: ReplayRequest) -> str:
    details = f"{request.method} {request.path}"
    if not request.params:
        return details

    return f"{details} params={dict(request.params)!r}"


def _request_from_fixture_path(relative_path: Path) -> ReplayRequest:
    if len(relative_path.parts) < 3:
        raise ValueError("local sample fixtures must include method, endpoint path, and file name")

    method = relative_path.parts[0]
    normalized_method = _normalize_method(method)
    if method != normalized_method:
        raise ValueError("fixture method directories must use canonical uppercase names")

    endpoint_parts = relative_path.parts[1:-1]
    params = _params_from_fixture_name(relative_path.name)
    return ReplayRequest(
        method=normalized_method,
        path="/" + "/".join(endpoint_parts),
        params=params,
    )


def _params_from_fixture_name(file_name: str) -> tuple[tuple[str, str], ...]:
    if not file_name.endswith(".json"):
        raise ValueError(f"unsupported replay fixture file type: {file_name}")

    stem = file_name[:-5]
    if stem == BASE_FIXTURE_NAME[:-5]:
        return ()

    params: list[tuple[str, str]] = []
    seen_keys: set[str] = set()
    for encoded_pair in stem.split(QUERY_PAIR_DELIMITER):
        if "=" not in encoded_pair:
            raise ValueError(f"invalid replay fixture query segment: {encoded_pair}")
        encoded_key, encoded_value = encoded_pair.split("=", 1)
        key = unquote(encoded_key)
        value = unquote(encoded_value)
        if not key:
            raise ValueError("fixture query parameter keys must not be empty")
        if key in seen_keys:
            raise ValueError(f"fixture query parameter keys must be unique: {key}")

        seen_keys.add(key)
        params.append((key, value))

    return tuple(sorted(params))
