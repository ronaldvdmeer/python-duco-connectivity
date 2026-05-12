"""Tests for the generated API reference inventory."""

from pathlib import Path

from tools.api_reference import (
    DOC_PATH,
    METHOD_METADATA,
    collect_method_references,
    collect_public_symbols,
    render_api_reference,
)


def test_method_metadata_covers_public_client_methods() -> None:
    """Every public async client method should be represented in the inventory."""
    references = collect_method_references()

    discovered_methods = {
        reference.name
        for category_references in references.values()
        for reference in category_references
    }

    assert discovered_methods == set(METHOD_METADATA)


def test_collect_public_symbols_groups_known_exports() -> None:
    """Known public exports should land in the expected sections."""
    symbols = collect_public_symbols()

    assert symbols["Client"] == ["DucoClient"]
    assert "VentilationState" in symbols["Enums"]
    assert "ConfigZone" in symbols["Models"]
    assert "DucoWriteLimitError" in symbols["Exceptions"]
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
    assert "`async_get_zone_config(" in content
    assert "-> ConfigZone`" in content


def test_doc_path_points_to_generated_file() -> None:
    """The helper should target the checked-in docs page."""
    assert DOC_PATH == Path(
        "/Users/ronald/SynologyDrive/Projecten/HomeAssistant/"
        "python-duco-connectivity/docs/api-reference.md"
    )
