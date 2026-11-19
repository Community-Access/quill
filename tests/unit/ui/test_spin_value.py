"""A spin control is read by what is typed in it, everywhere (Chris, 2026-11-19).

On Windows ``wx.SpinCtrlDouble`` answers ``GetValue()`` with its last
*committed* number, and typed text is only committed when focus leaves the box;
Enter or OK closes the dialog first. Typing 1.5 into Quill Cast's speed box
saved the old speed. :func:`quill.ui.spin_value.spin_value` reads the text.

The gate half fails on a ``.GetValue()`` of a name assigned from a spin
control anywhere in ``quill/`` or Quill Social, because the next one would
lose a typed number with nothing said.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from quill.ui.spin_value import spin_value

ROOT = Path(__file__).resolve().parents[3]
SCANNED = (ROOT / "quill", ROOT / "standalone" / "social")


class _Spin:
    """A spin control whose typed text has not been committed, as on Windows."""

    def __init__(self, value, text, low=0, high=100) -> None:
        self.value, self.text, self.low, self.high = value, text, low, high

    def GetValue(self):  # noqa: N802 - wx's name
        return self.value

    def GetTextValue(self) -> str:  # noqa: N802
        return self.text

    def SetValue(self, value) -> None:  # noqa: N802
        self.value = value

    def GetMin(self):  # noqa: N802
        return self.low

    def GetMax(self):  # noqa: N802
        return self.high


def test_typed_text_wins_and_is_committed() -> None:
    speed = _Spin(1.0, "1.5", 0.5, 5.0)
    assert spin_value(speed) == 1.5
    assert speed.value == 1.5  # the box now agrees with what was saved


@pytest.mark.parametrize(
    ("value", "text", "expected"),
    [
        (5, "42", 42),  # an int box stays an int
        (5, "", 5),  # nothing typed: the committed value stands
        (5, "4x", 5),  # half typed: the control's own answer
        (1.0, "9", 5.0),  # above the range: clamped, as the control would
        (1.0, "0.1", 0.5),  # below it
        (1.0, "1,25", 1.25),  # a decimal comma
    ],
)
def test_text_is_read_in_the_control_s_own_type_and_range(value, text, expected) -> None:
    high = 5.0 if isinstance(value, float) else 100
    low = 0.5 if isinstance(value, float) else 0
    got = spin_value(_Spin(value, text, low, high))
    assert got == expected and type(got) is type(expected)


def test_a_control_without_text_is_read_as_it_is() -> None:
    class Plain:
        def GetValue(self):  # noqa: N802
            return 7

    assert spin_value(Plain()) == 7


def test_on_a_real_wx_spin_control(wx_session_app) -> None:
    import wx

    frame = wx.Frame(None)
    try:
        box = wx.SpinCtrlDouble(frame, min=0.5, max=5.0, inc=0.05, initial=1.0)
        box.SetDigits(2)
        box.SetValue(1.25)
        assert spin_value(box) == pytest.approx(1.25)
    finally:
        frame.Destroy()


def _target(node: ast.expr) -> str:
    return ast.unparse(node)


def _spin_reads(tree: ast.AST) -> list[tuple[int, str]]:
    spins: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(node.value, ast.Call):
            func = node.value.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name in ("SpinCtrl", "SpinCtrlDouble"):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                spins.update(_target(t) for t in targets)
    found = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "GetValue"
            and not node.args
            and _target(node.func.value) in spins
        ):
            found.append((node.lineno, _target(node.func.value)))
    return found


def test_no_spin_control_is_read_by_its_committed_value_alone() -> None:
    offenders = []
    for root in SCANNED:
        for path in root.rglob("*.py"):
            if path.name == "spin_value.py":
                continue
            source = path.read_text(encoding="utf-8")
            if "SpinCtrl" not in source:
                continue
            for line, name in _spin_reads(ast.parse(source)):
                offenders.append(f"{path.relative_to(ROOT)}:{line}: {name}.GetValue()")
    assert not offenders, "read these with spin_value():\n" + "\n".join(offenders)
