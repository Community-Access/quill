"""QuillLite's rewrites are one undo step, because they go through QUILL's.

Reported while testing, twice in one sitting and about two different commands.
"I did the sort test and then pressed Ctrl+Z. The sort worked, but Ctrl+Z
returned a blank document. I had to press Ctrl+Z a second time to get the
original." And: "this is also true of Ctrl+Shift+U -- it seems to erase the
text, count that as an undo step and therefore requires a second keypress."

Neither is about sorting or about case. ``wxTextCtrl.Replace`` is recorded by
the native control as **two** entries, a delete and an insert, so the first
Ctrl+Z takes back the insert and leaves the delete standing -- an empty
document. QUILL established that in issue #131 and moved the working mechanism
into :mod:`quill.ui.atomic_edit`; QuillLite went on calling ``Replace`` in
twenty places while its own docstrings promised "Ctrl+Z takes back the sort as
one step" (bad.md C6 said as much and named only the clipboard and line paths).

What this asserts is the thing that actually broke: **no rewrite path in
QuillLite calls ``Replace`` directly any more.** A behavioural test of one
command would have passed throughout -- the sort sorted correctly the whole
time. It is the undo history that was wrong, and the only way to be wrong in it
is to use that call.

It matters more than the spelling of it suggests. Somebody who cannot see the
screen presses Ctrl+Z, hears an empty document, and cannot tell that apart from
having just lost the file -- and the obvious thing to try, pressing Ctrl+Z
again, looks exactly like making it worse.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_LITE = Path(__file__).resolve().parents[3] / "quill" / "apps"

#: The QuillLite modules that rewrite the document in place.
_EDITING_MODULES = sorted(_LITE.glob("lite_window_*.py"))


def _replace_calls(path: Path) -> list[str]:
    """Every ``<something>.control.Replace(...)`` call in *path*, by line."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "Replace":
            continue
        target = node.func.value
        if isinstance(target, ast.Attribute) and target.attr == "control":
            found.append(f"{path.name}:{node.lineno}")
    return found


def test_the_modules_are_actually_being_scanned() -> None:
    """A guard on the guard: a glob that matched nothing would pass silently."""
    assert len(_EDITING_MODULES) > 20


@pytest.mark.parametrize("module", _EDITING_MODULES, ids=lambda p: p.name)
def test_no_rewrite_calls_replace_directly(module: Path) -> None:
    direct = _replace_calls(module)
    assert not direct, (
        "control.Replace is two undo entries, so one Ctrl+Z leaves the document "
        "empty -- use quill.ui.atomic_edit.replace_as_one_undo instead:\n  " + "\n  ".join(direct)
    )


def test_the_rewrites_go_through_the_shared_helper() -> None:
    """And they reach it, rather than there being no rewrites left to find."""
    users = [m.name for m in _EDITING_MODULES if "replace_as_one_undo" in m.read_text("utf-8")]
    assert len(users) >= 9, users
