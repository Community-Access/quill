"""Unit tests for StructuredListSettings persistence and shipped presets (§3, §13)."""

from __future__ import annotations

from quill.core.lists.settings import (
    DefinitionMarkdownProfile,
    StructuredListSettings,
    list_studio_presets,
)


def test_to_dict_serializes_enum_as_value() -> None:
    settings = StructuredListSettings(definition_markdown_profile=DefinitionMarkdownProfile.PANDOC)
    data = settings.to_dict()
    assert data["definition_markdown_profile"] == "pandoc"
    assert data["verbosity"] == "standard"


def test_round_trip_through_dict_preserves_values() -> None:
    original = StructuredListSettings(
        markdown_loose=True,
        verbosity="detailed",
        ordered_delimiter=")",
        ordered_start=3,
        definition_markdown_profile=DefinitionMarkdownProfile.HTML_FALLBACK,
    )
    clone = StructuredListSettings.from_dict(original.to_dict())
    assert clone == original


def test_from_dict_ignores_unknown_and_malformed_fields() -> None:
    clone = StructuredListSettings.from_dict({
        "verbosity": "detailed",
        "ordered_start": "not-an-int",  # malformed -> keep default
        "definition_markdown_profile": "nonsense",  # invalid -> keep default
        "totally_unknown": 5,  # ignored
    })
    assert clone.verbosity == "detailed"
    assert clone.ordered_start == 1  # default preserved
    assert clone.definition_markdown_profile is DefinitionMarkdownProfile.ASK


def test_from_dict_non_dict_returns_defaults() -> None:
    assert StructuredListSettings.from_dict(None) == StructuredListSettings()
    assert StructuredListSettings.from_dict("oops") == StructuredListSettings()


def test_presets_are_named_settings_and_distinct() -> None:
    presets = list_studio_presets()
    assert "QUILL defaults" in presets
    assert all(isinstance(v, StructuredListSettings) for v in presets.values())
    assert presets["Loose Markdown lists"].markdown_loose is True
    assert (
        presets["Markdown (Pandoc definitions)"].definition_markdown_profile
        is DefinitionMarkdownProfile.PANDOC
    )
    assert presets["Detailed announcements"].verbosity == "detailed"


def test_presets_round_trip_through_dict() -> None:
    for preset in list_studio_presets().values():
        assert StructuredListSettings.from_dict(preset.to_dict()) == preset
