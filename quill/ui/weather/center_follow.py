"""The Weather Center's four lists keep the reader's row (FUX-06).

Every fetch used to ``Set()`` all four lists, which drops the selection and
puts a list box back at the top, and then forced each details box to the
first row while nothing was selected. Reading tomorrow's forecast and pressing
Refresh lost your place in all four lists at once.

Now each list changes row by row and keeps the reader on their own row by
identity: an alert by its id, a forecast period by its name, an hour by its
time, a day by its date. When the alert the reader was on has gone (it
expired, or was cancelled), the caller says so once and the reader is on the
alert that took its place. Kept out of ``weather_center_dialog`` so that
module stays under its size budget (GATE-11).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from quill.ui.list_stay_still import refill_listbox

__all__ = ["fill_list", "set_text", "sync_choice"]


def sync_choice(choice: Any, labels: list[str], index: int) -> None:
    """The place box, written only where it differs: it usually has focus right
    after a place is picked, and setting it again makes it be read again."""
    if labels != [choice.GetString(i) for i in range(choice.GetCount())]:
        choice.Set(labels)
    if index >= 0 and choice.GetSelection() != index:
        choice.SetSelection(index)


def set_text(box: Any, text: str) -> None:
    """Write a read-only box only when its words change: writing it again moves
    the caret to the start and refreshes braille for nothing."""
    if box.GetValue() != text:
        box.SetValue(text)


def fill_list(
    dialog: Any, name: str, listbox: Any, rows: Sequence[tuple[str, str]], empty: str
) -> tuple[int, str | None]:
    """Show *rows* (key, label) in *listbox*, keeping the reader's row.

    *empty* is the one row shown when there are none. Returns the row whose
    details to show (the reader's, else the first; -1 when there are none)
    and the key of the reader's row when it has gone (else ``None``).
    """
    attr = f"_follow_keys_{name}"
    old = getattr(dialog, attr, None)
    count = int(listbox.GetCount())
    if old is None or len(old) != count:
        old = []  # the placeholder row, or never filled
    index = int(listbox.GetSelection())
    wanted = old[index] if 0 <= index < len(old) else None
    if not rows:
        setattr(dialog, attr, [])
        if [listbox.GetString(i) for i in range(count)] != [empty]:
            listbox.Set([empty])
        return -1, wanted
    if not old and count:
        listbox.Clear()
    keys = [key for key, _label in rows]
    kept = refill_listbox(listbox, old, keys, [label for _key, label in rows], wanted)
    setattr(dialog, attr, keys)
    selection = int(listbox.GetSelection())
    return (selection if selection >= 0 else 0), (None if kept else wanted)
