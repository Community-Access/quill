"""Every hand-off of ``_show_modal_dialog`` is called with its label.

``MainFrame._show_modal_dialog(dialog, label)`` requires the label -- it is
what the dialog contract announces -- and a dialog module that receives the
bound method under a shorter name (``self._show_modal``) has no signature in
front of it when it calls. Two modules called it with one argument, and the
result was a TypeError **when the user pressed the button**, not at startup:
crash report #1442 (the Copilot Set Up flow), plus its unreported twin in the
agent validator, found while fixing it.

Source-level, because that is where the drift happens: the pattern
``._show_modal(self.dialog)`` with nothing after the argument is exactly the
call that compiles fine and crashes live.\n"""

from __future__ import annotations

import ast
import re
from pathlib import Path

_UI = Path(__file__).resolve().parents[3] / "quill" / "ui"

#: A one-argument call of a stored show-modal callable. The comma test is the
#: point: ``_show_modal(self.dialog, "Label")`` does not match.
_ONE_ARG_CALL = re.compile(r"\._show_modal\(\s*self\.(?:_)?dialog\s*\)")


def test_no_show_modal_call_omits_the_label() -> None:
    offenders = []
    for path in _UI.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in _ONE_ARG_CALL.finditer(text):
            line = text[: match.start()].count("\n") + 1
            offenders.append(f"{path.relative_to(_UI.parent.parent)}:{line}")
    assert not offenders, (
        "_show_modal called without its label (the #1442 crash shape):\n  " + "\n  ".join(offenders)
    )


def test_the_two_fixed_sites_pass_real_labels() -> None:
    copilot = (_UI / "copilot_onboarding_dialog.py").read_text(encoding="utf-8")
    validator = (_UI / "agent_validator_dialog.py").read_text(encoding="utf-8")
    assert '_show_modal(self.dialog, "Set Up GitHub Copilot")' in copilot
    assert '_show_modal(self.dialog, "Validate Agents")' in validator


#: The frame's own method and the names dialog modules store it under. Every
#: one of them is ``(dialog, label, ...)``; ``show_modal_dialog`` itself is
#: covered by ``test_show_modal_dialog_calls.py``.
_FRAME_SHOW_MODAL_NAMES = frozenset({
    "_show_modal_dialog",
    "_show_modal",
    "_show_modal_fn",
    "show_modal_fn",
    "_host_show_modal",
})


def frame_show_modal_calls_missing_label(source: str) -> list[int]:
    """Line numbers of frame show-modal calls that pass fewer than two arguments.

    An AST walk rather than the regex above, which only knew the
    ``self.dialog`` spelling: #1616 was the Copilot site again from an older
    build, and the sweep for it found ``host._show_modal_dialog(dialog)`` in
    the podcast chapter review -- a spelling the regex could not see.
    """
    found: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in _FRAME_SHOW_MODAL_NAMES:
            continue
        if any(isinstance(arg, ast.Starred) for arg in node.args):
            continue
        if any(kw.arg is None for kw in node.keywords):
            continue
        if len(node.args) >= 2 or any(kw.arg == "label" for kw in node.keywords):
            continue
        found.append(node.lineno)
    return found


def test_the_ast_detector_finds_every_spelling() -> None:
    source = (
        "def a(self, host, d):\n"
        "    host._show_modal_dialog(d)\n"  # line 2: bad
        "    self._show_modal(self.dialog)\n"  # line 3: bad
        "    self._show_modal_fn(d)\n"  # line 4: bad
        "    self._show_modal_dialog(d, 'Title')\n"
        "    self._show_modal(d, label='Title')\n"
        "    self._show_modal_dialog(*args)\n"
        "    dialog.show_modal()\n"  # a wrapper's own method, not the frame's
    )
    assert frame_show_modal_calls_missing_label(source) == [2, 3, 4]


def test_no_frame_show_modal_call_in_the_tree_omits_the_label() -> None:
    """#1442 and #1616: a one-argument call is a TypeError when the user presses the button."""
    root = _UI.parent
    offenders = []
    for path in sorted(root.rglob("*.py")):
        source = path.read_text(encoding="utf-8", errors="replace")
        for line in frame_show_modal_calls_missing_label(source):
            offenders.append(f"{path.relative_to(root.parent)}:{line}")
    joined = "\n  ".join(offenders)
    assert not offenders, f"frame show-modal called without its label:\n  {joined}"
