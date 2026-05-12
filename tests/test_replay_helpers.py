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
