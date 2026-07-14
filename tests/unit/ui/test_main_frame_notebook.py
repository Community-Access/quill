"""Source-contract test for the Manage Versions dialog's empty-state handling.

Live wx construction of MainFrame is impractical in this environment (matching
the repo's dialog-test convention elsewhere), so this asserts the wiring via
source text.
"""

from __future__ import annotations

from pathlib import Path

_NOTEBOOK = Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame_notebook.py"
_SRC = _NOTEBOOK.read_text(encoding="utf-8")


def test_manage_versions_shows_a_placeholder_when_no_versions_saved_yet() -> None:
    """Roadmap.md's "Snapshots vs Versions" empty-submenu report: a notebook
    with no saved Versions rendered Manage Versions' list as silently empty,
    with no explanation for a screen-reader user and no signal the feature was
    working as designed. A placeholder row (kept focusable/announced, unlike
    a disabled menu item) plus disabled Rename/Delete matches the existing
    "(No open documents in workspace)" precedent in main_frame_sessions.py."""
    method = _SRC[_SRC.index("def manage_notebook_snapshots") :][:2200]
    assert 'listbox.Append("(No versions saved yet)", None)' in method
    assert "if not snapshots:" in method
    assert "btn_rename.Enable(False)" in method
    assert "btn_delete.Enable(False)" in method


def test_manage_versions_rename_and_delete_guard_against_no_selection() -> None:
    """Defense in depth: even if a future change re-enables the buttons while
    the list is empty (or the placeholder row is somehow selected), on_rename
    and on_delete must still no-op rather than operate on a None snapshot id."""
    method = _SRC[_SRC.index("def manage_notebook_snapshots") :][:3200]
    assert "if idx == wx.NOT_FOUND:\n                return" in method
    assert "if snap is None:\n                return" in method
