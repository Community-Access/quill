"""GATE-KEYREF: docs/keyboard-reference.md is generated, never hand-written.

The reference is built from ``DEFAULT_KEYMAP`` / ``APP_KEYMAPS`` -- the same
tables the apps load -- so the only way for it to lie is to skip
regeneration, and this gate closes that: any keymap change that is not
reflected in the committed document fails here. (EdSharp's ``Hotkeys.md``
discipline: one table, several consumers, documentation that cannot drift.)
"""

from __future__ import annotations

from quill.tools import build_keymap_reference


def test_the_committed_reference_matches_the_keymap() -> None:
    committed = (
        build_keymap_reference.OUTPUT_PATH.read_text(encoding="utf-8")
        if build_keymap_reference.OUTPUT_PATH.exists()
        else ""
    )
    assert committed == build_keymap_reference.generate(), (
        "docs/keyboard-reference.md has drifted from DEFAULT_KEYMAP/APP_KEYMAPS. "
        "Regenerate with: python -m quill.tools.build_keymap_reference --write"
    )


def test_every_app_keymap_is_documented() -> None:
    from quill.core.app_keymaps import APP_KEYMAPS

    text = build_keymap_reference.OUTPUT_PATH.read_text(encoding="utf-8")
    for app_id, keymap in APP_KEYMAPS.items():
        for command_id in keymap:
            assert f"`{command_id}`" in text, f"{app_id}: {command_id} missing from the reference"


def test_titles_are_harvested_not_derived_for_the_menu_backed_commands() -> None:
    """A registration-table title must win over the id-derived fallback."""
    titles = build_keymap_reference.harvest_titles()
    # Two commands whose only human name lives in different table shapes:
    assert titles.get("file.open"), "register() harvest broken"
    assert titles.get("radio.browse"), "app-menu tuple harvest broken"
