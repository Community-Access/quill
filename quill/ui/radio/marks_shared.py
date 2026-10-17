"""The keys, menu rows and question every marking list shares (xradio2 4.10).

Marks began in Favorites (:mod:`quill.ui.radio.favorites_marks`) and now also
live in Recordings, Browse and the Schedule Recording list. What a mark *is*,
and every sentence said about one, is wx-free in
:mod:`quill.core.radio.row_marks`; this module is the part of the keyboard and
the screen that has to be the same everywhere, so a listener who learns it in
one list has learned it in all four:

* ``.`` (period, or the keypad's decimal point) marks or unmarks the selected
  row and says how many are marked. The row's own text gains "(marked)".
* **Delete**, while anything is marked, acts on **every** marked row after one
  question that says how many ("Delete 3 recordings?"), defaulting to No.
  With nothing marked it acts on the selected row exactly as before.
* **Ctrl+Shift+Delete** clears every mark and says how many it cleared.
* An action that uses only the selected row while rows are marked (Play, Edit,
  Open in Folder) says so once, and that the marks are still there, rather
  than leaving the listener to wonder what happened to them.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio.row_marks import RowMarks

__all__ = [
    "ACT",
    "CLEAR",
    "TOGGLE",
    "clear_marks",
    "is_mark_key",
    "mark_action",
    "mark_menu_entries",
    "marks_on",
    "say_ignored",
    "with_ignored_note",
    "yes_no_asker",
]

#: What :func:`mark_action` answers.
TOGGLE = "toggle"
ACT = "act"
CLEAR = "clear"


def is_mark_key(wx: Any, event: Any) -> bool:
    """Plain ``.`` or the keypad's decimal point, with no modifier held."""
    if event.ControlDown() or event.AltDown() or event.ShiftDown():
        return False
    return event.GetKeyCode() in (ord("."), getattr(wx, "WXK_NUMPAD_DECIMAL", -1))


def mark_action(wx: Any, event: Any) -> str | None:
    """Which marking key *event* is: :data:`TOGGLE`, :data:`ACT` (plain
    Delete), :data:`CLEAR` (Ctrl+Shift+Delete), or ``None``."""
    if is_mark_key(wx, event):
        return TOGGLE
    if event.GetKeyCode() not in (wx.WXK_DELETE, getattr(wx, "WXK_NUMPAD_DELETE", -1)):
        return None
    ctrl, shift, alt = event.ControlDown(), event.ShiftDown(), event.AltDown()
    if ctrl and shift and not alt:
        return CLEAR
    if ctrl or shift or alt:
        return None
    return ACT


def marks_on(owner: Any) -> RowMarks:
    """The marks a window holds, made on first use (kept off constructors
    that GATE-11 holds at their budgets)."""
    marks = getattr(owner, "_row_marks", None)
    if marks is None:
        marks = RowMarks()
        owner._row_marks = marks
    return marks


def with_ignored_note(owner: Any, said: str, verb: str = "Delete") -> str:
    """*said*, plus the once-per-set note when rows are marked and the action
    that produced *said* used only the selected one."""
    marks = getattr(owner, "_row_marks", None)
    note = marks.ignored_note(verb) if marks is not None else ""
    return f"{said} {note}".strip()


def say_ignored(owner: Any, verb: str = "Delete") -> None:
    """Speak the once-per-set note on its own, for an action whose outcome is
    otherwise shown rather than said (Edit fills a form and moves focus)."""
    note = with_ignored_note(owner, "", verb)
    if note:
        owner._announce(note)


def clear_marks(marks: RowMarks, *, announce: Callable[[str], None]) -> int:
    """Unmark everything and say how many were unmarked."""
    count = marks.clear()
    announce(f"Cleared {count} mark{'' if count == 1 else 's'}." if count else "Nothing marked.")
    return count


def mark_menu_entries(
    marks: RowMarks | None,
    *,
    toggle: Callable[[], None],
    remove: Callable[[], None],
    clear: Callable[[], None],
) -> list[tuple[str, Callable[[], None]]]:
    """The context-menu rows for marking, each showing its key.

    While anything is marked, Delete means "act on the marked rows", so the
    row that says so is the one carrying the Delete key -- the caller drops its
    single-row delete entry then, keeping one claimant per key.
    """
    entries: list[tuple[str, Callable[[], None]]] = [("Mark &for Deleting\t.", toggle)]
    if marks:
        entries.append((f"&Remove {len(marks)} Marked...\tDelete", remove))
        entries.append(("&Clear Marks\tCtrl+Shift+Delete", clear))
    return entries


def yes_no_asker(parent: Any, title: str) -> Callable[[str], bool]:
    """A yes/no question in a message box, defaulting to **No**: it is about
    many rows at once, and Enter pressed by habit should cost nothing."""

    def ask(question: str) -> bool:
        import wx

        answer = wx.MessageBox(  # MSGBOX-OK: parented confirmation for a shared action
            question,
            title,
            wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
            parent,
        )
        return bool(answer == wx.YES)

    return ask
