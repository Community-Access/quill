"""Tests for the QUILL key live cheat sheet (QK-2, QK-9)."""

from __future__ import annotations

from quill.core.quill_key_help import (
    MODE_BROWSE,
    MODE_PREFIX,
    build_cheat_sheet,
    format_cheat_sheet,
    summarize_cheat_sheet,
)


def _no_bindings(_command_id: str) -> str | None:
    return None


def test_prefix_mode_lists_core_follow_on_keys() -> None:
    groups = build_cheat_sheet(
        mode=MODE_PREFIX,
        binding_lookup=_no_bindings,
        counts={},
        selection_active=False,
    )
    assert len(groups) == 1
    keys = [entry.key for entry in groups[0].entries]
    assert "N" in keys
    assert "?" in keys
    assert "Escape" in keys
    assert "M" in keys
    assert "G" in keys
    # No selection: the selection-actions entry is absent.
    assert "A" not in keys


def test_prefix_mode_adds_selection_actions_when_selection_active() -> None:
    groups = build_cheat_sheet(
        mode=MODE_PREFIX,
        binding_lookup=_no_bindings,
        counts={},
        selection_active=True,
    )
    descriptions = " ".join(entry.description for entry in groups[0].entries)
    assert "Selection actions" in descriptions
    assert any(entry.key == "A" for entry in groups[0].entries)


def test_browse_mode_uses_default_keys_and_live_counts() -> None:
    counts = {
        "headings": 4,
        "links": 9,
        "lists": 2,
        "list_items": 7,
        "tables": 1,
        "block_quotes": 0,
        "bookmarks": 3,
        "code_blocks": 2,
        "paragraphs": 12,
        "sentences": 30,
        "heading_level_1": 1,
        "heading_level_2": 3,
    }
    groups = build_cheat_sheet(
        mode=MODE_BROWSE,
        binding_lookup=_no_bindings,
        counts=counts,
    )
    titles = [group.title for group in groups]
    assert "Move by structure" in titles
    assert "Jump to elements" in titles
    assert "Headings by level" in titles

    flat = {entry.key: entry for group in groups for entry in group.entries}
    # Default keys are surfaced when no binding is configured.
    assert flat["A"].description.lower().startswith("next or previous link")
    assert flat["A"].count == 9
    assert flat["L"].count == 2
    # Heading levels carry per-level counts.
    assert flat["1"].count == 1
    assert flat["2"].count == 3
    # A level with no count key reports None rather than zero.
    assert flat["6"].count is None


def test_browse_mode_respects_configured_bindings() -> None:
    def lookup(command_id: str) -> str | None:
        if command_id == "quill.quick_nav.link":
            return "K"
        return None

    groups = build_cheat_sheet(
        mode=MODE_BROWSE,
        binding_lookup=lookup,
        counts={"links": 5},
    )
    flat = {entry.key: entry for group in groups for entry in group.entries}
    assert "K" in flat
    assert flat["K"].count == 5
    # The default A is no longer used for links.
    assert "A" not in flat


def test_format_cheat_sheet_is_readable_text() -> None:
    groups = build_cheat_sheet(
        mode=MODE_PREFIX,
        binding_lookup=_no_bindings,
        counts={},
        selection_active=False,
    )
    text = format_cheat_sheet(groups)
    assert "QUILL key prefix" in text
    assert "Enter browse mode" in text
    assert text.endswith("\n")


def test_format_cheat_sheet_includes_counts() -> None:
    groups = build_cheat_sheet(
        mode=MODE_BROWSE,
        binding_lookup=_no_bindings,
        counts={"links": 9},
    )
    text = format_cheat_sheet(groups)
    assert "(9)" in text


def test_summarize_cheat_sheet_reports_totals() -> None:
    groups = build_cheat_sheet(
        mode=MODE_BROWSE,
        binding_lookup=_no_bindings,
        counts={},
    )
    summary = summarize_cheat_sheet(groups)
    assert summary.startswith("QUILL key help,")
    assert "groups" in summary


def test_unknown_mode_raises() -> None:
    import pytest

    with pytest.raises(ValueError):
        build_cheat_sheet(mode="nope", binding_lookup=_no_bindings, counts={})


def test_browse_mode_browse_groups_are_alphabetical() -> None:
    # #265: existing browse groups were not in alphabetical order. Pin the
    # sort so a future edit cannot silently regress the order back.
    groups = build_cheat_sheet(
        mode=MODE_BROWSE,
        binding_lookup=_no_bindings,
        counts={},
    )
    by_title = {group.title: group for group in groups}
    move_keys = [entry.key for entry in by_title["Move by structure"].entries]
    assert move_keys == sorted(move_keys, key=str.lower)
    jump_keys = [entry.key for entry in by_title["Jump to elements"].entries]
    assert jump_keys == sorted(jump_keys, key=str.lower)
    skip_keys = [entry.key for entry in by_title["Skip past containers"].entries]
    assert skip_keys == sorted(skip_keys, key=str.lower)


def test_browse_mode_chord_groups_grouped_by_category_and_alphabetical() -> None:
    # #265: the cheat sheet must surface every Ctrl+Shift+Grave chord
    # command, grouped by command prefix in fixed order
    # (File / Edit / Format / Navigate / View / Tools / Help) and
    # alphabetical within each group.
    chord_map = {
        "navigate.speak_window_title": "Ctrl+Shift+Grave, F",
        "view.send_to_tray": "Ctrl+Shift+Grave, T",
        "file.open_from_remote": "Ctrl+Shift+Grave, Shift+O",
        "tools.dictation_toggle": "Ctrl+Shift+Grave, D",
        "edit.copy_selection_for_email": "Ctrl+Shift+Grave, C",
        "format.toggle_line_comment": "Ctrl+Shift+Grave, Shift+;",
    }

    def lookup(command_id: str) -> str | None:
        return chord_map.get(command_id)

    groups = build_cheat_sheet(
        mode=MODE_BROWSE,
        binding_lookup=lookup,
        counts={},
        chord_map=chord_map,
        prefix="Ctrl+Shift+Grave",
    )
    titles = [group.title for group in groups]
    # Chord groups appear after the structural groups, in fixed category order.
    assert titles[-6:] == ["File", "Edit", "Format", "Navigate", "View", "Tools"]
    by_title = {group.title: group for group in groups}
    file_keys = [entry.key for entry in by_title["File"].entries]
    assert file_keys == ["Shift+O"]
    assert by_title["File"].entries[0].description == "Open From Remote"
    navigate_keys = [entry.key for entry in by_title["Navigate"].entries]
    assert navigate_keys == ["F"]
    assert by_title["Navigate"].entries[0].description == "Speak Window Title"
    tools_keys = [entry.key for entry in by_title["Tools"].entries]
    assert tools_keys == ["D"]


def test_browse_mode_chord_groups_respect_binding_lookup() -> None:
    # #265: when binding_lookup returns None for a chord command, the
    # command is treated as unbound and omitted from the cheat sheet.
    chord_map = {
        "navigate.speak_window_title": "Ctrl+Shift+Grave, F",
        "view.send_to_tray": "Ctrl+Shift+Grave, T",
    }

    def lookup(command_id: str) -> str | None:
        if command_id == "view.send_to_tray":
            return None
        return chord_map.get(command_id)

    groups = build_cheat_sheet(
        mode=MODE_BROWSE,
        binding_lookup=lookup,
        counts={},
        chord_map=chord_map,
        prefix="Ctrl+Shift+Grave",
    )
    titles = [group.title for group in groups]
    assert "View" not in titles
    navigate_group = next(g for g in groups if g.title == "Navigate")
    assert [entry.key for entry in navigate_group.entries] == ["F"]


def test_browse_mode_chord_groups_extract_second_key_from_full_binding() -> None:
    # #265: when the live keymap still has the full chord string
    # ("Ctrl+Shift+Grave, F") for the second key, the cheat sheet shows
    # just the second-key segment ("F") to the user.
    chord_map = {
        "navigate.speak_window_title": "Ctrl+Shift+Grave, F",
    }

    def lookup(command_id: str) -> str | None:
        # Live keymap returned the full chord string — the cheat sheet
        # must trim it to just the second key.
        return "Ctrl+Shift+Grave, F"

    groups = build_cheat_sheet(
        mode=MODE_BROWSE,
        binding_lookup=lookup,
        counts={},
        chord_map=chord_map,
        prefix="Ctrl+Shift+Grave",
    )
    navigate = next(g for g in groups if g.title == "Navigate")
    assert navigate.entries[0].key == "F"


def test_prefix_mode_does_not_include_chord_groups() -> None:
    # #265: the prefix cheat sheet (shown right after pressing the QUILL
    # key) stays a short list of follow-on mode gates. Chord commands
    # appear only in browse mode.
    chord_map = {
        "navigate.speak_window_title": "Ctrl+Shift+Grave, F",
        "view.send_to_tray": "Ctrl+Shift+Grave, T",
    }
    groups = build_cheat_sheet(
        mode=MODE_PREFIX,
        binding_lookup=_no_bindings,
        counts={},
        chord_map=chord_map,
        prefix="Ctrl+Shift+Grave",
    )
    titles = [group.title for group in groups]
    assert titles == ["QUILL key prefix"]


def test_browse_mode_chord_groups_skip_unrelated_bindings() -> None:
    # #265: only bindings whose prefix matches are surfaced. Bindings that
    # do not start with the configured prefix are left out.
    chord_map = {
        "navigate.speak_window_title": "Ctrl+Shift+Grave, F",
        "edit.copy": "Ctrl+C",  # not a QUILL chord
    }

    def lookup(command_id: str) -> str | None:
        return chord_map.get(command_id)

    groups = build_cheat_sheet(
        mode=MODE_BROWSE,
        binding_lookup=lookup,
        counts={},
        chord_map=chord_map,
        prefix="Ctrl+Shift+Grave",
    )
    titles = [group.title for group in groups]
    assert "Edit" not in titles
