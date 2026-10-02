"""Every call to ``show_modal_dialog`` passes the label it requires.

Found 2026-10-01 while giving Cast's Play Queue its title: three windows called
``show_modal_dialog(self.dialog)`` with no label, which has been a required
argument since the dialog contract grew one. Each raised ``TypeError`` the
moment it was opened -- the Play Queue (View > Play Queue in QUILL Cast, and
QUILL's own podcast host), the Global Hotkeys manager when opened without an
injected show function (QUILL Cast, Quill Radio), and QUILL's Sticky Notes
Browser. Nothing in the suite opened any of them for real, so nothing said so.

Static, by AST, over the whole tree: a call missing the label is a window that
cannot open, and that is cheap to see without building one.
"""

from __future__ import annotations

import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]


def missing_label_calls(source: str) -> list[int]:
    """Line numbers of ``show_modal_dialog(...)`` calls with no label."""
    found: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name != "show_modal_dialog":
            continue
        if any(isinstance(arg, ast.Starred) for arg in node.args):
            continue  # forwarded *args: the caller's problem, checked there
        if any(kw.arg is None for kw in node.keywords):
            continue  # forwarded **kwargs
        if len(node.args) >= 2 or any(kw.arg == "label" for kw in node.keywords):
            continue
        found.append(node.lineno)
    return found


def test_the_detector_finds_a_call_with_no_label() -> None:
    source = (
        "def a(d):\n"
        "    show_modal_dialog(d)\n"  # line 2: bad
        "    show_modal_dialog(d, 'Title')\n"
        "    show_modal_dialog(d, label='Title')\n"
        "    contract.show_modal_dialog(d)\n"  # line 5: bad
        "    show_modal_dialog(*args)\n"
    )
    assert missing_label_calls(source) == [2, 5]


def test_no_window_in_the_tree_calls_show_modal_dialog_without_its_label() -> None:
    hits: list[str] = []
    for path in sorted((_ROOT / "quill").rglob("*.py")):
        try:
            source = path.read_text(encoding="utf-8")
            lines = missing_label_calls(source)
        except SyntaxError:
            continue
        hits.extend(f"{path.relative_to(_ROOT).as_posix()}:{line}" for line in lines)
    assert hits == [], "show_modal_dialog needs its label, or the window cannot open: " + ", ".join(
        hits
    )
