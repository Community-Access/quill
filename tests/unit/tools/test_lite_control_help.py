"""Every control a QuillLite user can land on answers F1 with something specific.

GATE-LITE-HELP (``tests/unit/tools/test_lite_help_audit.py``) uses the family's
shared scanner, and that scanner's ``_HELPABLE_CLASSES`` is deliberately a
subset: it does not include ``wx.CheckBox``, and it cannot see a control built by
a factory in another module. Both gaps are real here --

* QuillLite's Find and Replace windows are half checkboxes;
* the **document itself** is built by
  :func:`quill.ui.richedit_editing.create_richedit_document`, so the control a
  listener is in for all but a few seconds of a session is invisible to the
  shared scan.

So this file asks the stricter question the product actually needs answered:
*of every focusable control QuillLite constructs, is there one without help?*
It is deliberately QuillLite's own rather than a change to the shared gate --
tightening that would put every sibling app into failure on a rule nobody has
agreed to yet.

The check is source-level (``ast``), so it needs no display and no wx.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
MODULES = sorted((REPO / "quill" / "apps").glob("lite*.py"))

#: Everything a Tab or an arrow key can land on. Broader than the shared gate's
#: set: a checkbox is exactly as landable-on as a text field, and a listener who
#: presses F1 on one deserves the same answer.
FOCUSABLE = frozenset({
    "Button",
    "CheckBox",
    "Choice",
    "ComboBox",
    "ListBox",
    "RadioButton",
    "RadioBox",
    "SearchCtrl",
    "Slider",
    "SpinCtrl",
    "SpinCtrlDouble",
    "TextCtrl",
    "ToggleButton",
    "TreeCtrl",
})

#: Constructions that are deliberately without help, and why. A read-only field
#: whose *content* is the answer has nothing a help sentence could add.
EXEMPT: dict[str, str] = {}


def _wx_class(func: ast.expr) -> str | None:
    if not isinstance(func, ast.Attribute):
        return None
    root: ast.expr = func.value
    while isinstance(root, ast.Attribute):
        root = root.value
    if isinstance(root, ast.Name) and root.id == "wx":
        return func.attr
    return None


def _assigned_name(parents: dict[ast.AST, ast.AST], call: ast.Call) -> str:
    """The name this construction is bound to (``self.text``, ``button``), or ""."""
    parent = parents.get(call)
    if isinstance(parent, ast.Assign) and len(parent.targets) == 1:
        return ast.unparse(parent.targets[0])
    if isinstance(parent, ast.AnnAssign):
        return ast.unparse(parent.target)
    return ""


def _helped_names(tree: ast.AST) -> set[str]:
    """Every target anywhere in the module that has ``SetHelpText`` called on it."""
    helped: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "SetHelpText"
        ):
            helped.add(ast.unparse(node.func.value))
    return helped


def _unhelped(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    helped = _helped_names(tree)
    findings: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        cls = _wx_class(node.func)
        if cls not in FOCUSABLE:
            continue
        if any(kw.arg == "helpText" for kw in node.keywords):
            continue
        name = _assigned_name(parents, node)
        key = f"{path.name}::{name or f'wx.{cls}'}:{node.lineno}"
        if key in EXEMPT:
            continue
        if not name or name not in helped:
            findings.append(f"{key} (wx.{cls})")
    return findings


@pytest.mark.parametrize("path", MODULES, ids=lambda p: p.name)
def test_every_focusable_control_carries_its_own_help(path: Path) -> None:
    findings = _unhelped(path)
    assert findings == [], (
        "These controls can be focused and have no SetHelpText, so F1 on them "
        "answers with the role sentence and nothing about what they are for:\n  "
        + "\n  ".join(findings)
    )


def test_the_scan_is_actually_looking_at_something() -> None:
    """A check that finds no controls passes everything."""
    assert MODULES, "no quill/apps/lite*.py modules found"
    total = 0
    for path in MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        total += sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and _wx_class(node.func) in FOCUSABLE
        )
    assert total >= 15, f"only {total} focusable controls found across {len(MODULES)} modules"


def test_the_document_control_itself_answers_f1_in_both_modes() -> None:
    """The control a listener is in almost all the time, and the one the shared
    scanner cannot see -- it is built by a factory in another module."""
    source = (REPO / "quill" / "apps" / "lite_window.py").read_text(encoding="utf-8")
    assert "def _apply_editor_help(self)" in source
    assert "self.control.SetHelpText(" in source
    for phrase in ("in rich text", "in plain text", "F6 moves to the status bar"):
        assert phrase in source, phrase
    # Re-applied whenever the mode changes, because what you can do in the
    # document differs by mode -- and the mode switch lives in the appearance
    # mixin, so the two calls are in two files by design.
    everywhere = "".join(path.read_text(encoding="utf-8") for path in MODULES)
    assert everywhere.count("self._apply_editor_help()") >= 2


def test_every_status_bar_cell_says_what_it_is() -> None:
    """The status bar is ten focusable buttons; each one is a question."""
    from quill.apps.lite_window_status import CELLS

    for cell in CELLS:
        assert cell.label and cell.help_text, cell.key
        assert len(cell.help_text) > 40, f"{cell.key}: help too thin to be worth reading"
        assert cell.help_text.rstrip().endswith("."), f"{cell.key}: help is not a sentence"
