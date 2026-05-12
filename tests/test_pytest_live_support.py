"""Tests for live-test pytest support helpers."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import pytest


def _load_module(path: Path, name: str) -> ModuleType:
    """Load a Python module from a file path for direct helper testing."""
    spec = spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TESTS_DIR = Path(__file__).resolve().parent
TESTS_CONFTEST = _load_module(TESTS_DIR / "conftest.py", "duco_tests_conftest")
LIVE_CONFTEST = _load_module(TESTS_DIR / "live" / "conftest.py", "duco_live_conftest")


class _FakeConfig:
    """Minimal config stub for collection hook tests."""

    def __init__(
        self,
        *,
        live: bool = False,
        live_writes: bool = False,
        live_performance: bool = False,
    ) -> None:
        self._options = {
            "--live": live,
            "--live-writes": live_writes,
            "--live-performance": live_performance,
        }

    def getoption(self, name: str) -> bool:
        """Return a configured boolean option."""
        return self._options[name]


class _FakeItem:
    """Minimal pytest item stub for collection hook tests."""

    def __init__(self, *keywords: str) -> None:
        self.keywords = {keyword: True for keyword in keywords}
        self.markers: list[pytest.MarkDecorator] = []

    def add_marker(self, marker: pytest.MarkDecorator) -> None:
        """Store markers added by the collection hook."""
        self.markers.append(marker)


@pytest.mark.parametrize("raw_value", ["nan", "inf", "-inf"])
def test_read_optional_float_env_rejects_non_finite_values(
    monkeypatch: pytest.MonkeyPatch,
    raw_value: str,
) -> None:
    """Non-finite float environment values should fail fast."""
    monkeypatch.setenv("DUCO_TEST_TIMEOUT", raw_value)

    with pytest.raises(
        pytest.fail.Exception,
        match=r"DUCO_TEST_TIMEOUT must be a finite float",
    ):
        LIVE_CONFTEST._read_optional_float_env("DUCO_TEST_TIMEOUT", default=10.0)


@pytest.mark.parametrize(
    ("keywords", "config", "expected_reasons"),
    [
        (
            ("live", "writes", "performance"),
            _FakeConfig(),
            ["need --live to run live Duco device tests"],
        ),
        (
            ("live", "writes"),
            _FakeConfig(live=True),
            ["need --live-writes to run live Duco write tests"],
        ),
        (
            ("live", "performance"),
            _FakeConfig(live=True),
            ["need --live-performance to run live Duco performance probes"],
        ),
    ],
)
def test_pytest_collection_modifyitems_applies_expected_skip_reason(
    keywords: tuple[str, ...],
    config: _FakeConfig,
    expected_reasons: list[str],
) -> None:
    """Collection-time skipping should report one reason per relevant gate."""
    item = _FakeItem(*keywords)

    TESTS_CONFTEST.pytest_collection_modifyitems(config, [item])

    reasons = [marker.kwargs["reason"] for marker in item.markers]
    assert reasons == expected_reasons
