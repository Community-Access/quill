"""Tests for the Structured List Studio scoped-settings precedence (§3)."""

from __future__ import annotations

from quill.core.lists.scopes import (
    diff_override,
    format_scope_override,
    resolve_settings,
)
from quill.core.lists.settings import DefinitionMarkdownProfile, StructuredListSettings


def test_no_overrides_returns_app_default() -> None:
    base = StructuredListSettings(verbosity="detailed", bullet_marker="*")
    assert resolve_settings(base) == base


def test_format_scope_pins_definition_profile() -> None:
    base = StructuredListSettings()  # ASK by default
    md = resolve_settings(base, format=format_scope_override("markdown"))
    html = resolve_settings(base, format=format_scope_override("html"))
    assert md.definition_markdown_profile is DefinitionMarkdownProfile.PANDOC
    assert html.definition_markdown_profile is DefinitionMarkdownProfile.HTML_FALLBACK
    # Only the profile field is touched; the rest is inherited.
    assert md.bullet_marker == base.bullet_marker


def test_document_scope_outranks_format() -> None:
    base = StructuredListSettings()
    resolved = resolve_settings(
        base,
        format=format_scope_override("markdown"),  # would set PANDOC
        document={"definition_markdown_profile": "multimarkdown"},
    )
    assert resolved.definition_markdown_profile is DefinitionMarkdownProfile.MULTIMARKDOWN


def test_document_field_survives_when_not_pinned_by_higher_scope() -> None:
    base = StructuredListSettings(markdown_loose=False)
    resolved = resolve_settings(
        base,
        format=format_scope_override("markdown"),
        document={"markdown_loose": True},
    )
    # The document pins markdown_loose; the format pin still owns the profile.
    assert resolved.markdown_loose is True
    assert resolved.definition_markdown_profile is DefinitionMarkdownProfile.PANDOC


def test_operation_outranks_document() -> None:
    base = StructuredListSettings()
    resolved = resolve_settings(
        base,
        document={"bullet_marker": "*"},
        operation={"bullet_marker": "+"},
    )
    assert resolved.bullet_marker == "+"


def test_unknown_override_keys_are_ignored() -> None:
    base = StructuredListSettings()
    resolved = resolve_settings(base, document={"nonexistent_field": 1, "bullet_marker": "+"})
    assert resolved.bullet_marker == "+"


def test_diff_override_captures_only_changed_fields() -> None:
    base = StructuredListSettings()
    changed = StructuredListSettings.from_dict(base.to_dict())
    changed.verbosity = "concise"
    changed.markdown_loose = True
    override = diff_override(changed, base)
    assert override == {"verbosity": "concise", "markdown_loose": True}


def test_diff_override_round_trips_through_resolve() -> None:
    base = StructuredListSettings()
    changed = StructuredListSettings.from_dict(base.to_dict())
    changed.bullet_marker = "*"
    changed.new_task_checked = True
    override = diff_override(changed, base)
    assert resolve_settings(base, document=override) == changed


def test_diff_override_empty_when_equal() -> None:
    base = StructuredListSettings()
    assert diff_override(StructuredListSettings.from_dict(base.to_dict()), base) == {}
