"""Each Cast window lands focus on the thing it is for (qc.md 6b).

The survey of 2026-09-30 found eight windows that landed focus on a filter or a
chooser rather than on what the listener opened them for. Five of them were a
one-line fix each; this pins those five: inside ``show()``, the named control is
focused before ``show_modal_dialog`` runs (ShowModal keeps a focus already
placed, and a focus set after it never happens, because it blocks).

Static, by AST, because the order of two calls in one method is a fact about the
source, and building five windows to learn it would test wx rather than Cast.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_PODCASTS = Path(__file__).resolve().parents[4] / "quill" / "ui" / "podcasts"

#: module -> the control that should hold focus when the window opens.
EXPECTED = {
    "downloads_dialog.py": "_list",
    # stats_dialog.py and year_review_dialog.py became peer windows in Phase 4:
    # open_peer focuses their focus_target() (the report) on every show, which
    # tests/unit/apps/test_cast_peer_windows.py pins.
    "play_queue_dialog.py": "_list",
}


def _show_method(tree: ast.AST) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "show":
            return node
    raise AssertionError("no show() method")


def _calls_in_order(method: ast.FunctionDef) -> list[tuple[int, str, str]]:
    """(line, callee, receiver attribute) for every call in *method*."""
    found: list[tuple[int, str, str]] = []
    for node in ast.walk(method):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        callee = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        receiver = ""
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Attribute):
            receiver = func.value.attr
        found.append((node.lineno, callee, receiver))
    return sorted(found)


@pytest.mark.parametrize(("module", "control"), sorted(EXPECTED.items()))
def test_the_window_focuses_its_purpose_before_it_is_shown(module: str, control: str) -> None:
    tree = ast.parse((_PODCASTS / module).read_text(encoding="utf-8"))
    calls = _calls_in_order(_show_method(tree))
    focus_lines = [line for line, callee, recv in calls if callee == "SetFocus" and recv == control]
    show_lines = [line for line, callee, _ in calls if callee == "show_modal_dialog"]
    assert focus_lines, f"{module}: show() never focuses self.{control}"
    assert show_lines, f"{module}: show() never calls show_modal_dialog"
    assert min(focus_lines) < min(show_lines), f"{module}: focus is set after the modal loop"
