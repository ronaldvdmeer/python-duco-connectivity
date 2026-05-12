"""Tests for sanitized replay fixture helpers."""

from pathlib import Path

import pytest

from tests.helpers.replay import (
    BASE_FIXTURE_NAME,
    RAW_REPLAY_FIXTURE_ROOT,
    SANITIZED_REPLAY_FIXTURE_ROOT,
    available_sanitized_replay_profiles,
    build_replay_request,
    build_sanitized_replay_fixture_path,
    load_sanitized_replay_fixture,
    load_sanitized_replay_fixture_set,
)

REPLAY_FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "replay"


def test_replay_fixture_roots_use_expected_repository_layout() -> None:
    """Replay helpers should point at the shared repository fixture tree."""
    assert SANITIZED_REPLAY_FIXTURE_ROOT == REPLAY_FIXTURE_ROOT / "sanitized"
    assert RAW_REPLAY_FIXTURE_ROOT == REPLAY_FIXTURE_ROOT / "raw"


def test_build_sanitized_replay_fixture_path_uses_stable_layout() -> None:
    """Fixture paths should be deterministic across path and query variants."""
    assert (
        build_sanitized_replay_fixture_path(
            "silent-connect-v25",
            "get",
            "/api",
        )
        == (REPLAY_FIXTURE_ROOT / "sanitized" / "silent-connect-v25" / "GET" / "api")
        / BASE_FIXTURE_NAME
    )

    assert build_sanitized_replay_fixture_path(
        "silent-connect-v25",
        "GET",
        "/info",
        params={"submodule": "Board", "module": "General"},
    ) == (
        REPLAY_FIXTURE_ROOT
        / "sanitized"
        / "silent-connect-v25"
        / "GET"
        / "info"
        / "module=General;submodule=Board.json"
    )

    assert (
        build_sanitized_replay_fixture_path(
            "silent-connect-v25",
            "GET",
            "/info/nodes",
        )
        == (REPLAY_FIXTURE_ROOT / "sanitized" / "silent-connect-v25" / "GET" / "info" / "nodes")
        / BASE_FIXTURE_NAME
    )


def test_available_sanitized_replay_profiles_lists_sample_profile() -> None:
    """Profile discovery should return sanitized profiles in sorted order."""
    assert available_sanitized_replay_profiles() == ("silent-connect-v25",)


def test_available_sanitized_replay_profiles_ignores_non_directory_root(
    tmp_path: Path,
) -> None:
    """Profile discovery should tolerate a misconfigured non-directory root."""
    root_file = tmp_path / "profiles.json"
    root_file.write_text("{}", encoding="utf-8")

    assert available_sanitized_replay_profiles(root=root_file) == ()


@pytest.mark.parametrize("profile", [".", ".."])
def test_replay_helpers_reject_relative_profile_names(profile: str) -> None:
    """Relative profile names should not be allowed to escape the fixture root."""
    with pytest.raises(ValueError, match=r"must not be \. or \.\."):
        build_sanitized_replay_fixture_path(profile, "GET", "/api")

    with pytest.raises(ValueError, match=r"must not be \. or \.\."):
        load_sanitized_replay_fixture_set(profile)


def test_replay_helpers_reject_portability_breaking_profile_names() -> None:
    """Profile names should remain portable across operating systems."""
    with pytest.raises(ValueError, match="simple directory name"):
        build_sanitized_replay_fixture_path("silent\\connect-v25", "GET", "/api")

    with pytest.raises(ValueError, match="simple directory name"):
        load_sanitized_replay_fixture_set("silent\\connect-v25")


@pytest.mark.parametrize("profile", ["silent:connect-v25", "silent*connect-v25", "SilentConnect"])
def test_replay_helpers_reject_non_portable_profile_slugs(profile: str) -> None:
    """Profile names should use the documented portable slug format."""
    with pytest.raises(ValueError, match="portable slug"):
        build_sanitized_replay_fixture_path(profile, "GET", "/api")

    with pytest.raises(ValueError, match="portable slug"):
        load_sanitized_replay_fixture_set(profile)


@pytest.mark.parametrize(
    ("path", "message"),
    [
        ("//info", "must not start with //"),
        ("/info\\nodes", "must use / separators only"),
    ],
)
def test_replay_helpers_reject_ambiguous_path_separators(
    path: str,
    message: str,
) -> None:
    """Replay helper paths should reject ambiguous separators."""
    with pytest.raises(ValueError, match=message):
        build_sanitized_replay_fixture_path("silent-connect-v25", "GET", path)


def test_load_sanitized_replay_fixture_returns_single_fixture() -> None:
    """Single fixture loads should preserve the normalized request key."""
    fixture = load_sanitized_replay_fixture(
        "silent-connect-v25",
        "GET",
        "/info",
        params={"submodule": "Board", "module": "General"},
    )

    assert fixture.request == build_replay_request(
        "GET",
        "/info",
        params={"module": "General", "submodule": "Board"},
    )
    assert fixture.payload == {
        "General": {
            "Board": {
                "PublicApiVersion": {"Val": "2.5"},
                "BoxName": {"Val": "SILENT_CONNECT"},
                "BoxSubTypeName": {"Val": "Eu"},
            }
        }
    }


def test_load_sanitized_replay_fixture_set_loads_profile_index() -> None:
    """Loading a profile should index each fixture by normalized request."""
    fixture_set = load_sanitized_replay_fixture_set("silent-connect-v25")

    assert set(fixture_set) == {
        build_replay_request("GET", "/api"),
        build_replay_request(
            "GET",
            "/info",
            params={"module": "General", "submodule": "Board"},
        ),
        build_replay_request("GET", "/info/nodes"),
    }
    assert fixture_set[build_replay_request("GET", "/api")].payload == {
        "PublicApiVersion": {"Val": "2.5"},
        "ApiInfo": [],
    }


def test_load_sanitized_replay_fixture_set_rejects_missing_profile() -> None:
    """Missing replay profiles should fail explicitly."""
    with pytest.raises(FileNotFoundError, match="missing-profile"):
        load_sanitized_replay_fixture_set("missing-profile")


def test_load_sanitized_replay_fixture_reports_params_and_path_on_missing_fixture(
    tmp_path: Path,
) -> None:
    """Missing fixtures should report both the normalized request and target file."""
    with pytest.raises(FileNotFoundError) as err:
        load_sanitized_replay_fixture(
            "silent-connect-v25",
            "GET",
            "/info",
            params={"submodule": "Board", "module": "General"},
            root=tmp_path,
        )

    message = str(err.value)
    assert "GET /info" in message
    assert "params={'module': 'General', 'submodule': 'Board'}" in message
    assert "module=General;submodule=Board.json" in message


def test_load_sanitized_replay_fixture_set_reports_profile_root_on_missing_profile(
    tmp_path: Path,
) -> None:
    """Missing profiles should report the resolved profile path."""
    with pytest.raises(FileNotFoundError) as err:
        load_sanitized_replay_fixture_set("missing-profile", root=tmp_path)

    assert str(tmp_path / "missing-profile") in str(err.value)


def test_load_sanitized_replay_fixture_set_reports_conflicting_files(
    tmp_path: Path,
) -> None:
    """Duplicate normalized fixtures should point to both conflicting files."""
    profile_root = tmp_path / "silent-connect-v25" / "GET" / "info"
    profile_root.mkdir(parents=True)
    first_fixture = profile_root / "module=General;submodule=Board.json"
    second_fixture = profile_root / "submodule=Board;module=General.json"
    first_fixture.write_text("{}", encoding="utf-8")
    second_fixture.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError) as err:
        load_sanitized_replay_fixture_set("silent-connect-v25", root=tmp_path)

    message = str(err.value)
    assert "GET /info" in message
    assert str(first_fixture) in message
    assert str(second_fixture) in message


@pytest.mark.parametrize(
    ("file_name", "message"),
    [
        ("=value.json", "must not be empty"),
        ("a=1;a=2.json", "must be unique: a"),
    ],
)
def test_load_sanitized_replay_fixture_set_rejects_invalid_fixture_query_keys(
    tmp_path: Path,
    file_name: str,
    message: str,
) -> None:
    """On-disk fixture params should match the same key invariants as request params."""
    profile_root = tmp_path / "silent-connect-v25" / "GET" / "info"
    profile_root.mkdir(parents=True)
    (profile_root / file_name).write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_sanitized_replay_fixture_set("silent-connect-v25", root=tmp_path)


def test_load_sanitized_replay_fixture_set_rejects_noncanonical_method_directory(
    tmp_path: Path,
) -> None:
    """On-disk fixtures should use canonical uppercase method directories."""
    profile_root = tmp_path / "silent-connect-v25" / "get" / "info"
    profile_root.mkdir(parents=True)
    (profile_root / BASE_FIXTURE_NAME).write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="canonical uppercase"):
        load_sanitized_replay_fixture_set("silent-connect-v25", root=tmp_path)
