"""One undo step, one story, both editors (bad.md C6).

The two editors documented opposite facts about the same wx call. QUILL's
``_atomic_replace`` said native ``TextCtrl.Replace`` is recorded as *two* undo
entries and refused to use it (issue #131); QUILL Lite's clipboard insert and
line operations promised "one undoable step" and used ``Replace`` to get it.
Both sentences were written in good faith and one of them was wrong, and the
way to find out which was to press Ctrl+Z after a line move and read the
result -- which, for the person this editor is built for, means having the
whole document read back to work out what state it is in.

QUILL's story is the verified one. ``tests/unit/ui/test_main_frame_undo_atomic.py``
drives real wx controls and asserts it both ways round: after
``ctrl.Replace(0, last, upper)`` a single ``Undo()`` leaves the control
**empty**, and after selecting the range and writing over it a single ``Undo()``
restores exactly the original text with earlier history intact.

So this module holds the one mechanism, both editors call it, and the claim is
true wherever it is made. It takes the control rather than importing ``wx``:
there is nothing here that needs the toolkit, and staying out of it keeps the
helper testable against the same stubs the rest of the suite uses.
"""

from __future__ import annotations

from typing import Any, Protocol

__all__ = ["replace_as_one_undo"]


class _TextControl(Protocol):  # pragma: no cover - a shape, not behaviour
    def SetSelection(self, start: int, end: int) -> None: ...
    def WriteText(self, text: str) -> None: ...


def replace_as_one_undo(control: Any, start: int, end: int, text: str) -> None:
    """Replace ``[start, end)`` in *control* with *text* as a single undo step.

    Selecting the range and writing over it is what the native control records
    as one reversible edit; ``Replace`` is not, and ``SetValue`` is worse still
    because it discards the undo history entirely.

    Falls back to ``Replace`` only for a stub that has no selection/write pair,
    which is a test double rather than a surface a person edits in.
    """
    set_selection = getattr(control, "SetSelection", None)
    write_text = getattr(control, "WriteText", None)
    if callable(set_selection) and callable(write_text):
        set_selection(start, end)
        write_text(text)
        return
    control.Replace(start, end, text)  # pragma: no cover - minimal stubs only
