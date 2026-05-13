"""Tests for replay fixture sanitization tooling."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_replay_sanitizer_module():
    module_path = Path(__file__).resolve().parents[1] / "tools" / "replay_sanitizer.py"
    spec = importlib.util.spec_from_file_location("replay_sanitizer", module_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_replay_sanitizer_scrubs_installation_specific_values() -> None:
    """The sanitizer should preserve box identity while scrubbing local details."""
    replay_sanitizer = _load_replay_sanitizer_module()
    sanitizer = replay_sanitizer.ReplaySanitizer()
    payload = {
        "General": {
            "Board": {
                "BoxName": {"Val": "DUCOBOX_ENERGY"},
                "BoxSubTypeName": {"Val": "Eu"},
                "PublicApiVersion": {"Val": "2.5"},
                "SerialBoardComm": {"Val": "PS2424005629"},
            },
            "Lan": {
                "Ip": {"Val": "192.168.3.94"},
                "NetMask": {"Val": "255.255.255.0"},
                "DucoClientIp": {"Val": "0.0.0.0"},
                "Mac": {"Val": "a0:dd:6c:06:12:90"},
                "HostName": {"Val": "duco_061293"},
                "WifiClientSsid": {"Val": "my-network"},
                "WifiApKey": {"Val": "12345678"},
            },
        },
        "Nodes": [
            {
                "General": {
                    "Name": {"Val": "Kitchen valve"},
                }
            }
        ],
    }

    sanitized = sanitizer.sanitize(payload)

    assert sanitized["General"]["Board"]["BoxName"]["Val"] == "DUCOBOX_ENERGY"
    assert sanitized["General"]["Board"]["BoxSubTypeName"]["Val"] == "Eu"
    assert sanitized["General"]["Board"]["PublicApiVersion"]["Val"] == "2.5"
    assert sanitized["General"]["Board"]["SerialBoardComm"]["Val"] == "sanitized-serial-1"
    assert sanitized["General"]["Lan"]["Ip"]["Val"] == "192.0.2.1"
    assert sanitized["General"]["Lan"]["NetMask"]["Val"] == "255.255.255.0"
    assert sanitized["General"]["Lan"]["DucoClientIp"]["Val"] == "0.0.0.0"
    assert sanitized["General"]["Lan"]["Mac"]["Val"] == "02:00:00:00:00:01"
    assert sanitized["General"]["Lan"]["HostName"]["Val"] == "sanitized-hostname-1"
    assert sanitized["General"]["Lan"]["WifiClientSsid"]["Val"] == "sanitized-ssid-1"
    assert sanitized["General"]["Lan"]["WifiApKey"]["Val"] == "sanitized-secret-1"
    assert sanitized["Nodes"][0]["General"]["Name"]["Val"] == "sanitized-name-1"


def test_sanitize_replay_profile_preserves_layout_and_reuses_replacements(
    tmp_path: Path,
) -> None:
    """Profile conversion should mirror the layout and keep replacements stable."""
    replay_sanitizer = _load_replay_sanitizer_module()
    raw_root = tmp_path / "raw"
    sanitized_root = tmp_path / "sanitized"
    profile_root = raw_root / "ducobox-focus-v25"

    first_raw_file = profile_root / "get" / "info" / "nodes" / "__base__.json"
    first_raw_file.parent.mkdir(parents=True)
    first_raw_file.write_text(
        json.dumps(
            {
                "Nodes": [
                    {
                        "General": {"Name": {"Val": "Kitchen valve"}},
                        "Lan": {"Ip": {"Val": "192.168.1.25"}},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    second_raw_file = profile_root / "GET" / "info" / "module=General;submodule=Board.json"
    second_raw_file.parent.mkdir(parents=True, exist_ok=True)
    second_raw_file.write_text(
        json.dumps(
            {
                "General": {
                    "Board": {"BoxName": {"Val": "DUCOBOX_FOCUS"}},
                    "Zones": [{"Name": {"Val": "Kitchen valve"}}],
                }
            }
        ),
        encoding="utf-8",
    )

    written_paths = replay_sanitizer.sanitize_replay_profile(
        "ducobox-focus-v25",
        raw_root=raw_root,
        sanitized_root=sanitized_root,
    )

    expected_board_path = (
        sanitized_root
        / "ducobox-focus-v25"
        / "GET"
        / "info"
        / "module=General;submodule=Board.json"
    )
    expected_nodes_path = (
        sanitized_root / "ducobox-focus-v25" / "GET" / "info" / "nodes" / "__base__.json"
    )

    assert written_paths == [expected_board_path, expected_nodes_path]

    first_sanitized = json.loads(written_paths[0].read_text(encoding="utf-8"))
    second_sanitized = json.loads(written_paths[1].read_text(encoding="utf-8"))

    assert first_sanitized["General"]["Board"]["BoxName"]["Val"] == "DUCOBOX_FOCUS"
    assert first_sanitized["General"]["Zones"][0]["Name"]["Val"] == "sanitized-name-1"
    assert second_sanitized["Nodes"][0]["General"]["Name"]["Val"] == "sanitized-name-1"
    assert second_sanitized["Nodes"][0]["Lan"]["Ip"]["Val"] == "192.0.2.1"


def test_sanitize_replay_profile_supports_flat_raw_export_files(tmp_path: Path) -> None:
    """Flat export files from device captures should map to deterministic replay paths."""
    replay_sanitizer = _load_replay_sanitizer_module()
    raw_root = tmp_path / "raw"
    sanitized_root = tmp_path / "sanitized"
    profile_root = raw_root / "Energy"
    profile_root.mkdir(parents=True)

    (profile_root / "ENERGY_info.json").write_text(
        json.dumps(
            {
                "General": {
                    "Board": {
                        "BoxName": {"Val": "ENERGY"},
                        "PublicApiVersion": {"Val": "2.7"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (profile_root / "ENERGY_config_zones.json").write_text(
        json.dumps(
            {"Zones": [{"DeviceGroupConfig": {"General": {"Name": {"Val": "Living room"}}}}]}
        ),
        encoding="utf-8",
    )

    written_paths = replay_sanitizer.sanitize_replay_profile(
        "ducobox-energy-v27",
        raw_profile="Energy",
        raw_root=raw_root,
        sanitized_root=sanitized_root,
    )

    assert written_paths == [
        sanitized_root / "ducobox-energy-v27" / "GET" / "config" / "zones" / "__base__.json",
        sanitized_root / "ducobox-energy-v27" / "GET" / "info" / "__base__.json",
    ]

    info_payload = json.loads(written_paths[1].read_text(encoding="utf-8"))
    zone_payload = json.loads(written_paths[0].read_text(encoding="utf-8"))

    assert info_payload["General"]["Board"]["BoxName"]["Val"] == "ENERGY"
    assert info_payload["General"]["Board"]["PublicApiVersion"]["Val"] == "2.7"
    assert (
        zone_payload["Zones"][0]["DeviceGroupConfig"]["General"]["Name"]["Val"]
        == "sanitized-name-1"
    )
