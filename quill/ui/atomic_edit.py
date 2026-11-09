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

__all__ = ["edits_as_one_undo", "replace_as_one_undo"]


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


def edits_as_one_undo(control: Any, edits: list[tuple[int, int, str]]) -> None:
    """Make several small *edits* ``(start, end, text)`` in *control* as one undo step.

    For a change that touches a few places in a long document -- the line
    starts of an Indent -- where replacing the whole span would rewrite it as
    plain text and drop a rich document's headings and bold (review
    2026-11-09, QUILL Lite 1). Positions are the control's, against the text
    *before* any edit; they are applied last first so each stays true.

    Grouped by Rich Edit's own edit collection where the control has one; a
    control without it gets one undo entry per edit rather than a failure.
    """
    ordered = sorted(edits, key=lambda edit: edit[0], reverse=True)
    if len(ordered) == 1:
        replace_as_one_undo(control, *ordered[0])
        return
    with _edit_collection(control):
        for start, end, text in ordered:
            replace_as_one_undo(control, start, end, text)


class _NoCollection:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *_exc: object) -> None:
        return None


def _edit_collection(control: Any) -> Any:
    """Rich Edit's ``BeginEditCollection`` around a block, or nothing at all."""
    get_handle = getattr(control, "GetHandle", None)
    if not callable(get_handle):
        return _NoCollection()
    try:
        from quill.ui.richedit_rtf_surface import _one_undo_step

        return _one_undo_step(int(get_handle()))
    except Exception:  # noqa: BLE001 - grouping is an improvement, never a gate
        return _NoCollection()
