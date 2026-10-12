"""Quill Cast must not expand a hidden tree root (startup crash).

Found by the #1299 smoke pass: launching Quill Cast died before its window
appeared with

    wx._core.wxAssertionError: C++ assertion ""!IsHiddenRoot(item)"" failed
    in wxTreeCtrl::DoExpand(): Can't expand/collapse hidden root node!

The shows tree is created with ``TR_HIDE_ROOT``, and wxMSW refuses to expand a
hidden root. A hidden root is always effectively expanded anyway -- its children
*are* the visible top level -- so the call was never doing anything except
crashing the app.

A source assertion rather than a live wx test: constructing the real frame needs
a podcast library on disk, and the bug is a static "do not call this on a hidden
root" contract.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
# The shows tree is built in ui/podcasts/main_panel.py since the 2026-10
# integration; the app module and every Cast UI module are scanned, so moving
# the tree again cannot quietly drop the guard.
_TREE_SOURCE = _ROOT / "quill" / "ui" / "podcasts" / "main_panel.py"
_CAST_SOURCES = [
    _ROOT / "quill" / "apps" / "podcasts.py",
    *sorted((_ROOT / "quill" / "ui" / "podcasts").glob("*.py")),
    *sorted((_ROOT / "quill" / "ui").glob("main_frame_podcast*.py")),
]


def test_the_shows_tree_hides_its_root() -> None:
    source = _TREE_SOURCE.read_text(encoding="utf-8")
    assert "wx.TR_HIDE_ROOT" in source


def test_expanding_the_root_is_guarded_by_the_hide_root_style() -> None:
    # Any expansion of a root must be the line right after the hidden-root
    # guard, or a later edit could drift them apart and restore the crash.
    for path in _CAST_SOURCES:
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
        for index, line in enumerate(lines):
            if line in ("tree.Expand(root)", "self._shows_tree.Expand(root)"):
                assert lines[index - 1] == "if not (tree.GetWindowStyle() & wx.TR_HIDE_ROOT):", (
                    f"{path.name}:{index + 1} expands a root without the hidden-root guard"
                )
