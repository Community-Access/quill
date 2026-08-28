"""GATE-13: no announcement may repeat what the screen reader already says.

The written rule lives in CLAUDE.md beside the menu-accelerator rule; the
mechanics live in ``quill.tools.check_over_announce``. Three shapes are
banned -- announcing from an ``EVT_SET_FOCUS`` handler, announcing a window
title via ``GetTitle()``, and announcing a string literal that is also a
``title=`` literal in the same file -- because each is a mechanical way to
say something twice, and a duplicated announcement is never filed as a bug,
only absorbed as chattiness.
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

from quill.tools import check_over_announce


def test_the_live_tree_has_no_over_announcements() -> None:
    violations = check_over_announce.scan()
    assert violations == [], "\n".join(str(v) for v in violations)


def _violations_of(source: str) -> list[str]:
    tree = ast.parse(textwrap.dedent(source))
    # Reuse the file checker through a temp-free path: build the pieces the
    # way _check_file does, on this source alone.
    title_literals = set(check_over_announce._TITLE_KWARG_RE.findall(textwrap.dedent(source)))
    focus_handlers = check_over_announce._focus_handler_names(tree)
    found: list[str] = []
    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(func):
            if not isinstance(node, ast.Call) or not check_over_announce._is_announce_call(node):
                continue
            if func.name in focus_handlers:
                found.append("focus")
                continue
            arg = check_over_announce._sole_arg(node)
            if arg is None:
                continue
            if check_over_announce._is_get_title_call(arg):
                found.append("gettitle")
            elif (
                isinstance(arg, ast.Constant)
                and isinstance(arg.value, str)
                and arg.value in title_literals
            ):
                found.append("title-literal")
    found.extend("lambda-focus" for _ in check_over_announce._lambda_focus_announces(tree))
    return found


def test_announce_in_focus_handler_is_flagged() -> None:
    source = """
        class D:
            def build(self):
                self.ctrl.Bind(wx.EVT_SET_FOCUS, self._on_focus)

            def _on_focus(self, event):
                self._announce("Search field")
                event.Skip()
    """
    assert _violations_of(source) == ["focus"]


def test_announce_of_gettitle_is_flagged() -> None:
    source = """
        class D:
            def open(self):
                self._announce(self.GetTitle())
    """
    assert _violations_of(source) == ["gettitle"]


def test_announce_of_title_literal_is_flagged() -> None:
    source = """
        class D:
            def build(self):
                dlg = wx.Dialog(self, title="Manage Stations")
                self._announce("Manage Stations")
    """
    assert _violations_of(source) == ["title-literal"]


def test_lambda_focus_announce_is_flagged() -> None:
    source = """
        class D:
            def build(self):
                self.ctrl.Bind(wx.EVT_SET_FOCUS, lambda e: self._announce("here"))
    """
    assert _violations_of(source) == ["lambda-focus"]


def test_the_gate12_fix_pattern_is_not_flagged() -> None:
    """Announcing a status label after SetLabel is GATE-12's cure, not a bug."""
    source = """
        class D:
            def update(self, message):
                self._status.SetLabel(message)
                self._announce(self._status.GetLabel())
    """
    assert _violations_of(source) == []


def test_ordinary_announces_are_not_flagged() -> None:
    source = """
        class D:
            def done(self, count):
                self._announce(f"{count} stations imported")

            def _on_key(self, event):
                self._announce("Recording started")
    """
    assert _violations_of(source) == []


def test_the_rule_is_written_down() -> None:
    """The CLAUDE.md rule and the gate must exist together."""
    claude_md = (Path(__file__).resolve().parents[3] / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Speak only what the screen reader does not already say" in claude_md
