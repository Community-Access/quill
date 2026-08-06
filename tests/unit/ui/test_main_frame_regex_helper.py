"""Source-level pins for the Regular Expression Helper surface (#1328 P1).

The helper used to live inline in main_frame.py; it is now a thin delegation
to quill.ui.regex_helper_dialog (behavior tests: test_regex_helper_dialog.py).
These pins keep the delegation and the dialog's accessible-control contract
from silently regressing.
"""

from __future__ import annotations

from pathlib import Path

_UI = Path(__file__).resolve().parents[3] / "quill" / "ui"


def test_main_frame_delegates_to_the_dialog_module() -> None:
    source = (_UI / "main_frame.py").read_text(encoding="utf-8")
    assert "def show_regex_helper(self) -> None:" in source
    assert "from quill.ui.regex_helper_dialog import open_regex_helper" in source
    assert "open_regex_helper(self)" in source
    # The old inline dialog must not creep back into the monolith.
    assert 'title="Regular Expression Helper"' not in source


def test_regex_helper_dialog_uses_accessible_controls() -> None:
    source = (_UI / "regex_helper_dialog.py").read_text(encoding="utf-8")
    assert 'title="Regular Expression Helper"' in source
    assert "wx.TreeCtrl(" in source, "recipes present as a category tree"
    assert 'set_accessible_name(tree, "Recipes by category")' in source
    assert "wx.TE_MULTILINE | wx.TE_READONLY" in source, "explanation/results are reviewable"
    assert "apply_modal_ids(" in source
    assert "_show_modal_dialog(dialog" in source, "goes through the shared modal contract"


def test_regex_helper_dialog_supports_preview_copy_and_use() -> None:
    source = (_UI / "regex_helper_dialog.py").read_text(encoding="utf-8")
    assert "explain_pattern" in source, "live plain-language explanations"
    assert "run_pattern" in source, "bounded preview execution"
    assert "controller._copy_to_clipboard(pattern)" in source
    assert "Use in &Find All Matches" in source
    assert "use_regex=True" in source, "the Use button turns regex mode on"


def test_regex_helper_speaks_explanation_and_preview() -> None:
    """The live explain pane and preview must reach screen-reader users: the
    debounced explanation and the Preview/Enter run speak through the same
    controller._announce channel Find uses (desktop-a11y review #1/#2)."""
    source = (_UI / "regex_helper_dialog.py").read_text(encoding="utf-8")
    assert "controller._announce(" in source, "explanation/preview are spoken"
    assert "refresh_explanation(announce=True)" in source, "debounced typing speaks the summary"
    assert "render_preview(announce=True)" in source, "Preview/Enter speak the result summary"
