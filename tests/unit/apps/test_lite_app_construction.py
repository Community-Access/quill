"""The wx.App itself can be constructed, which no other test checks.

Every other QuillLite test builds a stub window (``tests/unit/apps/conftest.py``)
because a real ``wx.App`` needs a display. That is the right trade for testing
commands -- and it left ``QuillLiteApp.__init__`` with no test at all, so on
2026-09-17 it could read ``self.settings`` at line 88 while ``OnInit`` set it at
line 121, and **QuillLite did not start**. The only thing that constructs the
real app is the live probe, which is run by hand.

This does not need a display: ``__init__`` is plain Python up to the
``super().__init__`` call, and what broke was in that plain Python. Checking the
attribute order is enough to catch the whole class of fault, which is a
constructor reaching for state a later phase sets.
"""

from __future__ import annotations

import ast
from pathlib import Path

LITE = Path(__file__).resolve().parents[3] / "quill" / "apps" / "lite.py"


def _assigned_and_read(method: str) -> tuple[set[str], set[str]]:
    """``(attributes assigned, attributes read)`` on ``self`` in *method*."""
    tree = ast.parse(LITE.read_text(encoding="utf-8"))
    node = next(
        n
        for cls in ast.walk(tree)
        if isinstance(cls, ast.ClassDef) and cls.name == "QuillLiteApp"
        for n in cls.body
        if isinstance(n, ast.FunctionDef) and n.name == method
    )
    assigned: set[str] = set()
    read: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name):
            if sub.value.id != "self":
                continue
            (assigned if isinstance(sub.ctx, ast.Store) else read).add(sub.attr)
    return assigned, read


def test_init_never_reads_state_that_oninit_sets() -> None:
    """The fault that stopped QuillLite starting, in one assertion.

    ``__init__`` runs before ``OnInit``. An attribute read in the first and
    assigned only in the second is an AttributeError on launch -- and
    ``getattr(self.settings, "x", default)`` does not protect it, because the
    default covers a missing *field*, not a missing ``self.settings``.
    """
    init_assigned, init_read = _assigned_and_read("__init__")
    oninit_assigned, _ = _assigned_and_read("OnInit")

    too_early = sorted((init_read & oninit_assigned) - init_assigned)
    assert too_early == [], (
        f"__init__ reads {too_early}, which OnInit sets later -- QuillLite will "
        "raise AttributeError before its first window appears"
    )


def test_settings_is_one_of_the_attributes_oninit_owns() -> None:
    """Guards the guard: if settings ever moved into __init__ the test above
    would pass for the wrong reason, having nothing left to compare."""
    oninit_assigned, _ = _assigned_and_read("OnInit")
    assert "settings" in oninit_assigned
