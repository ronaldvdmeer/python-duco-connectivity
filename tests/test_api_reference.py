"""Tests for the generated API reference inventory."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "api_reference.py"
SPEC = importlib.util.spec_from_file_location("api_reference", MODULE_PATH)
if SPEC is None:
    raise RuntimeError(f"Unable to load module spec for {MODULE_PATH}")
if SPEC.loader is None:
    raise RuntimeError(f"Unable to load module loader for {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

DOC_PATH = MODULE.DOC_PATH
METHOD_METADATA = MODULE.METHOD_METADATA
collect_method_references = MODULE.collect_method_references
collect_public_symbols = MODULE.collect_public_symbols
render_api_reference = MODULE.render_api_reference


def test_method_metadata_covers_public_client_methods() -> None:
    """Every public async client method should be represented in the inventory."""
    references = collect_method_references()

    discovered_methods = {
        reference.name
        for category_references in references.values()
        for reference in category_references
    }

    assert discovered_methods == set(METHOD_METADATA)


def test_collect_method_references_follow_metadata_order() -> None:
    """Rendered method order should be driven by the metadata inventory."""
    references = collect_method_references()

    discovered_methods = [
        reference.name
        for category_references in references.values()
        for reference in category_references
    ]

    assert discovered_methods == list(METHOD_METADATA)


def test_collect_public_symbols_groups_known_exports() -> None:
    """Known public exports should land in the expected sections."""
    symbols = collect_public_symbols()

    assert symbols["Client"] == ["DucoClient"]
    assert "VentilationState" in symbols["Enums"]
    assert "InfoModuleSelector" in symbols["Enums"]
    assert "ConfigZone" in symbols["Models"]
    assert "DucoWriteLimitError" in symbols["Exceptions"]
    assert symbols["Compatibility exports"] == ["ApiEndpointInfo", "DucoRateLimitError"]
    assert symbols["Other"] == ["__version__"]


def test_rendered_api_reference_is_current() -> None:
    """The checked-in API reference should match the generator output."""
    expected = render_api_reference()

    assert DOC_PATH.read_text(encoding="utf-8") == expected


def test_api_reference_contains_expected_sections() -> None:
    """The generated page should expose the main navigation sections."""
    content = render_api_reference()

    assert "# API reference" in content
    assert "## Client construction" in content
    assert "## Client methods" in content
    assert "## Public exports" in content
    assert "## Compatibility details" in content
    assert "## See also" in content
    assert "### Compatibility exports" in content
    assert "`ApiEndpointInfo`" in content
    assert "`async_get_zone_config(" in content
    assert "-> ConfigZone`" in content
    assert "selectors.md" in content


def test_api_reference_documents_optional_capability_contracts() -> None:
    """Optional endpoint return and exception contracts should stay explicit."""
    content = render_api_reference()

    assert "optional endpoint as unsupported" in content
    assert "without the requested target field in the response" in content
    assert "optional target endpoint is unsupported" in content


def test_api_reference_hides_compatibility_only_method_aliases() -> None:
    """Compatibility-only client aliases should not be published as documented methods."""
    content = render_api_reference()

    assert "async_get_write_req_remaining" not in content


def test_doc_path_points_to_generated_file() -> None:
    """The helper should target the checked-in docs page."""
    assert DOC_PATH == ROOT / "docs" / "api-reference.md"
