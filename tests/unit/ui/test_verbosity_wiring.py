"""Source-contract tests for the verbosity main_frame wiring (sub-PR 1.5)."""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_UI = _ROOT / "quill" / "ui"


def _src(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


def test_mixin_in_main_frame_mro() -> None:
    src = _src("quill/ui/main_frame.py")
    assert "from quill.ui.main_frame_verbosity import VerbosityCommandsMixin" in src
    assert "VerbosityCommandsMixin," in src


def test_verbosity_commands_registered() -> None:
    src = _src("quill/ui/main_frame_commands.py")
    for cmd in (
        "verbosity.toggle_quiet",
        "verbosity.toggle_meeting",
        "verbosity.undo",
        "verbosity.preferences",
        "verbosity.where_am_i",
        "verbosity.what_changed",
        "verbosity.speak_status",
    ):
        assert f'"{cmd}"' in src, f"{cmd} not registered in main_frame"


def test_announce_routes_through_controller_when_present() -> None:
    src = _src("quill/ui/main_frame.py")
    assert "_route_verbosity_announcement" in src
    assert "_verbosity_controller" in src


def test_prefs_dialog_registered_in_inventory() -> None:
    fixture = Path(__file__).parent / "fixtures" / "dialog_inventory.json"
    inv = json.loads(fixture.read_text(encoding="utf-8"))
    # The mixin hosts the prefs panel in a modal dialog.
    keys = [k for k in inv if "main_frame_verbosity.py" in k and "wx.Dialog" in k]
    assert keys, "Verbosity preferences dialog not registered"
    assert all(inv[k] == "hardened_custom" for k in keys)


def test_mixin_applies_modal_ids() -> None:
    assert "apply_modal_ids" in _src("quill/ui/main_frame_verbosity.py")


def test_chords_bound_in_the_defaults() -> None:
    """The three verbosity chords, asserted where they belong.

    They used to be asserted against ``profile_default.json``, which was the
    only place they were bound -- and a profile is a *delta* over the defaults
    (bad.md P2.6), so a command bound only there is invisible to the Keyboard
    Manager and the generated reference, and pinned to whatever it said in
    2025. Ctrl+Shift+Z is the proof: the profile still claimed it for
    verbosity.undo months after it became Quick Nav in the defaults.
    """
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP["verbosity.toggle_quiet"] == "Ctrl+Shift+Grave, Shift+Q"
    assert DEFAULT_KEYMAP["verbosity.toggle_meeting"] == "Ctrl+Shift+Grave, Shift+M"
    assert DEFAULT_KEYMAP["verbosity.undo"] == "Ctrl+Shift+Grave, Shift+Z"
    chords = [v for v in DEFAULT_KEYMAP.values() if v]
    assert len(chords) == len(set(chords)), "two commands on one chord"


def test_quote_lines_binding_preserved() -> None:
    # Regression guard: verbosity must not have stolen Ctrl+Shift+Q from quote_lines.
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP["edit.quote_lines"] == "Ctrl+Shift+Q"
