"""Tests for the function probe CLI."""

import json
from types import TracebackType
from typing import Any
from unittest.mock import ANY

import pytest

from duco_connectivity import BoardInfo, DucoError
from duco_connectivity import cli as duco_cli


class _FakeClientSession:
    """Minimal async context manager for ClientSession patches."""

    async def __aenter__(self) -> "_FakeClientSession":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        return False


def test_call_board_info_outputs_json_without_raw_payload(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI should serialize dataclass results without raw payloads by default."""
    init_calls: list[dict[str, Any]] = []

    class FakeClient:
        def __init__(
            self,
            session: object,
            host: str,
            *,
            port: int | None = None,
            request_timeout: float = 10.0,
        ) -> None:
            init_calls.append(
                {
                    "session": session,
                    "host": host,
                    "port": port,
                    "request_timeout": request_timeout,
                }
            )

        async def async_get_board_info(self) -> BoardInfo:
            return BoardInfo(
                box_name="SILENT_CONNECT",
                box_sub_type_name="Eu",
                serial_board_box="RS2420002577",
                serial_board_comm="PS2424005629",
                serial_duco_box="n/a",
                serial_duco_comm="P369348-241126-033",
                time=1778454913,
                public_api_version="2.6",
                software_version="1.2.3",
                raw_payload={"BoxName": {"Val": "SILENT_CONNECT"}},
            )

    monkeypatch.setattr(duco_cli.aiohttp, "ClientSession", _FakeClientSession)
    monkeypatch.setattr(duco_cli, "DucoClient", FakeClient)

    result = duco_cli.main(["--host", "192.0.2.94", "call", "async_get_board_info"])

    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert output["box_name"] == "SILENT_CONNECT"
    assert "raw_payload" not in output
    assert init_calls == [
        {
            "session": ANY,
            "host": "192.0.2.94",
            "port": None,
            "request_timeout": 10.0,
        }
    ]


def test_call_board_info_can_include_raw_payload(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI should include raw payloads when explicitly requested."""

    class FakeClient:
        def __init__(
            self,
            session: object,
            host: str,
            *,
            port: int | None = None,
            request_timeout: float = 10.0,
        ) -> None:
            del session, host, port, request_timeout

        async def async_get_board_info(self) -> BoardInfo:
            return BoardInfo(
                box_name="SILENT_CONNECT",
                box_sub_type_name="Eu",
                serial_board_box="RS2420002577",
                serial_board_comm="PS2424005629",
                serial_duco_box="n/a",
                serial_duco_comm="P369348-241126-033",
                time=1778454913,
                public_api_version="2.6",
                software_version="1.2.3",
                raw_payload={"BoxName": {"Val": "SILENT_CONNECT"}},
            )

    monkeypatch.setattr(duco_cli.aiohttp, "ClientSession", _FakeClientSession)
    monkeypatch.setattr(duco_cli, "DucoClient", FakeClient)

    result = duco_cli.main(
        [
            "--host",
            "192.0.2.94",
            "--include-raw-payload",
            "call",
            "async_get_board_info",
        ]
    )

    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert output["raw_payload"] == {"BoxName": {"Val": "SILENT_CONNECT"}}


def test_call_node_info_forwards_method_parameters(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI should forward the supported method arguments unchanged."""
    calls: list[dict[str, Any]] = []

    class FakeClient:
        def __init__(
            self,
            session: object,
            host: str,
            *,
            port: int | None = None,
            request_timeout: float = 10.0,
        ) -> None:
            del session, host, port, request_timeout

        async def async_get_node_info(
            self,
            node_id: int,
            module: str | None = None,
            parameter: str | None = None,
        ) -> dict[str, Any]:
            calls.append(
                {
                    "node_id": node_id,
                    "module": module,
                    "parameter": parameter,
                }
            )
            return calls[-1]

    monkeypatch.setattr(duco_cli.aiohttp, "ClientSession", _FakeClientSession)
    monkeypatch.setattr(duco_cli, "DucoClient", FakeClient)

    result = duco_cli.main(
        [
            "--host",
            "192.0.2.94",
            "call",
            "async_get_node_info",
            "--node-id",
            "7",
            "--module",
            "General",
            "--parameter",
            "Name",
        ]
    )

    assert result == 0
    assert json.loads(capsys.readouterr().out) == {
        "node_id": 7,
        "module": "General",
        "parameter": "Name",
    }
    assert calls == [{"node_id": 7, "module": "General", "parameter": "Name"}]


def test_call_requires_node_id_for_node_methods(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Node-specific probe methods should fail early without their required id."""

    class FakeClient:
        def __init__(
            self,
            session: object,
            host: str,
            *,
            port: int | None = None,
            request_timeout: float = 10.0,
        ) -> None:
            del session, host, port, request_timeout

    monkeypatch.setattr(duco_cli.aiohttp, "ClientSession", _FakeClientSession)
    monkeypatch.setattr(duco_cli, "DucoClient", FakeClient)

    result = duco_cli.main(["--host", "192.0.2.94", "call", "async_get_node_info"])

    assert result == 2
    assert "async_get_node_info requires --node-id" in capsys.readouterr().err


def test_call_rejects_unsupported_method_flags(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI should reject flags that are not part of the chosen method signature."""

    class FakeClient:
        def __init__(
            self,
            session: object,
            host: str,
            *,
            port: int | None = None,
            request_timeout: float = 10.0,
        ) -> None:
            del session, host, port, request_timeout

        async def async_get_board_info(self) -> BoardInfo:
            return BoardInfo(
                box_name="SILENT_CONNECT",
                box_sub_type_name="Eu",
                serial_board_box="RS2420002577",
                serial_board_comm="PS2424005629",
                serial_duco_box="n/a",
                serial_duco_comm="P369348-241126-033",
                time=1778454913,
                public_api_version="2.6",
                software_version="1.2.3",
                raw_payload={},
            )

    monkeypatch.setattr(duco_cli.aiohttp, "ClientSession", _FakeClientSession)
    monkeypatch.setattr(duco_cli, "DucoClient", FakeClient)

    result = duco_cli.main(
        [
            "--host",
            "192.0.2.94",
            "call",
            "async_get_board_info",
            "--node-id",
            "7",
        ]
    )

    assert result == 2
    assert "async_get_board_info does not support --node-id" in capsys.readouterr().err


def test_compatibility_alias_is_not_exposed_by_cli() -> None:
    """Compatibility-only client aliases should not be probeable from the CLI."""
    parser = duco_cli.build_parser()
    subparsers_action = next(action for action in parser._actions if action.dest == "command")
    call_parser = subparsers_action.choices["call"]
    method_action = next(action for action in call_parser._actions if action.dest == "method")

    assert "async_get_write_req_remaining" not in duco_cli.METHOD_SPECS
    assert "async_get_write_req_remaining" not in method_action.choices


def test_call_raw_parses_query_items(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Raw probes should pass repeated query items as a params mapping."""
    calls: list[dict[str, Any]] = []

    class FakeClient:
        def __init__(
            self,
            session: object,
            host: str,
            *,
            port: int | None = None,
            request_timeout: float = 10.0,
        ) -> None:
            del session, host, port, request_timeout

        async def async_get_raw(
            self,
            path: str,
            *,
            params: dict[str, str] | None = None,
        ) -> dict[str, Any]:
            calls.append({"path": path, "params": params})
            return calls[-1]

    monkeypatch.setattr(duco_cli.aiohttp, "ClientSession", _FakeClientSession)
    monkeypatch.setattr(duco_cli, "DucoClient", FakeClient)

    result = duco_cli.main(
        [
            "--host",
            "192.0.2.94",
            "call",
            "async_get_raw",
            "--path",
            "/info",
            "--query",
            "module=General",
            "--query",
            "submodule=Board",
        ]
    )

    assert result == 0
    assert json.loads(capsys.readouterr().out) == {
        "path": "/info",
        "params": {"module": "General", "submodule": "Board"},
    }
    assert calls == [{"path": "/info", "params": {"module": "General", "submodule": "Board"}}]


def test_call_raw_rejects_invalid_query_items(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Malformed query items should return a usage-style error code."""

    class FakeClient:
        def __init__(
            self,
            session: object,
            host: str,
            *,
            port: int | None = None,
            request_timeout: float = 10.0,
        ) -> None:
            del session, host, port, request_timeout

    monkeypatch.setattr(duco_cli.aiohttp, "ClientSession", _FakeClientSession)
    monkeypatch.setattr(duco_cli, "DucoClient", FakeClient)

    result = duco_cli.main(
        [
            "--host",
            "192.0.2.94",
            "call",
            "async_get_raw",
            "--path",
            "/info",
            "--query",
            "module",
        ]
    )

    assert result == 2
    assert "Invalid query item: module. Use KEY=VALUE." in capsys.readouterr().err


def test_call_reports_duco_errors_to_stderr(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Duco exceptions should fail the CLI with a non-zero exit code."""

    class FakeClient:
        def __init__(
            self,
            session: object,
            host: str,
            *,
            port: int | None = None,
            request_timeout: float = 10.0,
        ) -> None:
            del session, host, port, request_timeout

        async def async_get_board_info(self) -> BoardInfo:
            raise DucoError("boom")

    monkeypatch.setattr(duco_cli.aiohttp, "ClientSession", _FakeClientSession)
    monkeypatch.setattr(duco_cli, "DucoClient", FakeClient)

    result = duco_cli.main(["--host", "192.0.2.94", "call", "async_get_board_info"])

    assert result == 1
    assert capsys.readouterr().err.strip() == "boom"
