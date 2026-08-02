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

_SOURCE = Path(__file__).resolve().parents[3] / "quill" / "apps" / "podcasts.py"


def test_the_shows_tree_hides_its_root() -> None:
    source = _SOURCE.read_text(encoding="utf-8")
    assert "wx.TR_HIDE_ROOT" in source


def test_expanding_the_root_is_guarded_by_the_hide_root_style() -> None:
    source = _SOURCE.read_text(encoding="utf-8")

    assert "if not (tree.GetWindowStyle() & wx.TR_HIDE_ROOT):" in source
    # The guard has to be the line immediately before the Expand, or a later
    # edit could drift them apart and restore the crash.
    lines = [line.strip() for line in source.splitlines()]
    expand_lines = [i for i, line in enumerate(lines) if line == "tree.Expand(root)"]
    assert expand_lines, "the root expansion moved; re-check the hidden-root guard"
    for index in expand_lines:
        assert lines[index - 1] == "if not (tree.GetWindowStyle() & wx.TR_HIDE_ROOT):"
