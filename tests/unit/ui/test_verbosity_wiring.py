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
    src = _src("quill/ui/main_frame.py")
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


def test_chords_bound_in_default_profile() -> None:
    b = json.loads(
        (_ROOT / "quill" / "core" / "keymap" / "profile_default.json").read_text(encoding="utf-8")
    )["bindings"]
    assert b["verbosity.toggle_quiet"] == "Ctrl+Shift+Grave, Q"
    assert b["verbosity.toggle_meeting"] == "Ctrl+Shift+Grave, Shift+Q"
    assert b["verbosity.undo"] == "Ctrl+Shift+Z"
    # No chord collisions among bound bindings.
    chords = [v for v in b.values() if isinstance(v, str) and v]
    assert len(chords) == len(set(chords))


def test_quote_lines_binding_preserved() -> None:
    # Regression guard: verbosity must not have stolen Ctrl+Shift+Q from quote_lines.
    b = json.loads(
        (_ROOT / "quill" / "core" / "keymap" / "profile_default.json").read_text(encoding="utf-8")
    )["bindings"]
    assert b["edit.quote_lines"] == "Ctrl+Shift+Q"
