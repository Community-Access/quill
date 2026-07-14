"""Source pins: tabbed dialogs must not park initial focus on the tab strip.

A screen-reader user who opens a tabbed dialog should land on the first control
of the active tab, not on the notebook (tab strip) itself -- otherwise they hear
a tab, assume it is the first field, and down-arrow into nothing. Initial focus
is routed centrally by ``dialog_contract.focus_primary_control`` (now
notebook-aware: it drills into the selected page). These pins fail if a swept
dialog re-introduces an explicit ``notebook.SetFocus`` override that clobbers the
seam, and confirm the module-level dialogs still apply the seam themselves.

Mirrors the source-pin pattern in ``test_ai_hub_lazy_string_regression.py``.
"""

from __future__ import annotations

from pathlib import Path

_UI = Path(__file__).resolve().parents[3] / "quill" / "ui"


def _src(name: str) -> str:
    return (_UI / name).read_text(encoding="utf-8")


def test_ai_hub_does_not_force_focus_onto_the_notebook() -> None:
    src = _src("ai_hub_dialog.py")
    assert "self._notebook.SetFocus" not in src, (
        "AI Hub must not focus the notebook tab strip on open; initial focus is "
        "handled by _show_modal_dialog's focus_primary_control seam."
    )


def test_about_dialogs_route_focus_through_the_contract() -> None:
    src = _src("info_pages.py")
    assert "notebook.SetFocus" not in src, (
        "The About dialogs must not focus the notebook tab strip on open."
    )
    # Both tabbed About dialogs (About Quill, About BITS Whisperer) use the
    # module-level show_modal_dialog (no MainFrame seam), so each must call
    # focus_primary_control itself.
    assert src.count("focus_primary_control(dialog)") >= 2, (
        "Each tabbed About dialog must call focus_primary_control itself."
    )


def test_status_dialog_routes_focus_through_the_contract() -> None:
    src = _src("status_dialog.py")
    assert "self.dialog.SetFocus()" not in src, (
        "The non-modal status dialog must not focus the dialog (which forwards "
        "to the notebook tab strip); it must route through focus_primary_control."
    )
    assert "focus_primary_control(self.dialog)" in src, (
        "The status dialog is shown non-modally, so it must call focus_primary_control itself."
    )


def test_quillin_prefs_dialog_routes_focus_through_the_contract() -> None:
    src = _src("quillin_prefs_dialog.py")
    assert "notebook.SetFocus" not in src, (
        "The Quillin preferences dialog must not focus the notebook tab strip."
    )
    assert "focus_primary_control(dialog)" in src, (
        "The Quillin preferences dialog uses the module-level show_modal_dialog, "
        "so it must call focus_primary_control itself."
    )
