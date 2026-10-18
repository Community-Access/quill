"""Marks in the Recordings window: mark many, delete them with one question.

The Favorites marking keys (:mod:`quill.ui.radio.marks_shared`), on the
Recordings list. Only a **finished** recording can be marked: one still
recording has no file to delete yet, and a scheduled row is not a file at all
(its schedule lives in Schedule Recording). Pressing ``.`` on either says so
rather than doing nothing.

Delete with recordings marked removes every one of them after one question
("Delete 3 recordings?", default No). The files are held aside the same way a
single delete holds one, so **Ctrl+Z brings all of them back** in one step.
The cursor then lands on the nearest surviving row, never back at the top.

Split from ``recordings_manager_dialog`` under GATE-11, beside its sibling
:mod:`quill.ui.radio.recordings_delete`, which still owns the one-row delete.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.counted import plural
from quill.core.radio.recordings_index import STATUS_RECORDED, STATUS_RECORDING
from quill.core.radio.row_marks import delete_question, deleted_sentence, landing_after
from quill.ui.radio.marks_shared import (
    ACT,
    CLEAR,
    TOGGLE,
    clear_marks,
    mark_action,
    marks_on,
    yes_no_asker,
)

__all__ = ["on_key", "remove", "remove_marked", "toggle_selected"]

_NOUN = "recording"


def _markable(entry: Any) -> bool:
    return entry is not None and entry.status == STATUS_RECORDED and entry.path is not None


def toggle_selected(dialog: Any) -> None:
    """Mark or unmark the selected recording, saying the running count."""
    entry = dialog._selected()
    if entry is None:
        return
    if not _markable(entry):
        if entry.status == STATUS_RECORDING:
            dialog._announce("Still recording; it can be marked once it has finished.")
        else:
            dialog._announce("Only finished recordings can be marked.")
        return
    marks = marks_on(dialog)
    now_marked = marks.toggle(entry.id)
    dialog._set_row(dialog._list.GetFirstSelected(), entry)
    dialog._announce(marks.toggle_sentence(now_marked))


def remove(dialog: Any) -> None:
    """Delete and the Remove button: every marked recording when any are
    marked, otherwise the selected one, as before."""
    marks = marks_on(dialog)
    marks.keep_only(entry.id for entry in dialog._entries if _markable(entry))
    if marks:
        remove_marked(dialog)
        return
    from quill.ui.radio import recordings_delete

    recordings_delete.remove_selected(dialog)


def remove_marked(dialog: Any, *, ask: Callable[[str], bool] | None = None) -> bool:
    """Ask once, then delete every marked recording. Returns whether any went."""
    marks = marks_on(dialog)
    doomed = [entry for entry in dialog._entries if _markable(entry) and entry.id in marks]
    if not doomed:
        return False
    asker = ask or yes_no_asker(dialog.dialog, "Delete Marked Recordings")
    if not asker(delete_question(len(doomed), _NOUN)):
        dialog._announce("Nothing was deleted.")
        return False
    order = [entry.id for entry in dialog._entries]
    current = dialog._selected()
    landing = landing_after(order, current.id if current else None, marks.keys)
    from quill.ui import undo_last_ui

    paths = [entry.path for entry in doomed]
    held = undo_last_ui.hold_or_delete(paths)
    failed = 0
    if not held:
        for path in paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                failed += 1

    def _undo() -> None:
        undo_last_ui.restore(held)
        dialog._refresh(keep_selection=False)

    removed = len(doomed) - failed
    undo_last_ui.remember(
        "Delete Recordings",
        plural(removed, _NOUN),
        "",
        _undo,
        dispose=lambda: undo_last_ui.discard(held),
    )
    marks.clear()
    dialog._announce(undo_last_ui.offer(deleted_sentence(removed, _NOUN, failed=failed)))
    dialog._refresh(keep_selection=False)
    _land(dialog, landing)
    return removed > 0


def _land(dialog: Any, entry_id: str | None) -> None:
    """Put the cursor on the surviving row *entry_id* (or say none are left)."""
    rows = [entry.id for entry in dialog._entries]
    if entry_id is None or entry_id not in rows:
        if not rows:
            dialog._announce("No recordings left.")
            return
        entry_id = rows[0]
    row = rows.index(entry_id)
    dialog._list.Select(row)
    dialog._list.Focus(row)
    dialog._list.EnsureVisible(row)
    dialog._on_selection_changed()


def on_key(dialog: Any, event: Any) -> None:
    """The list's key handler: the marking keys, then everything else."""
    action = mark_action(dialog._wx, event)
    if action == TOGGLE:
        toggle_selected(dialog)
    elif action == ACT:
        remove(dialog)
    elif action == CLEAR:
        clear_marks(marks_on(dialog), announce=dialog._announce)
        for row, entry in enumerate(dialog._entries):
            dialog._set_row(row, entry)
    else:
        event.Skip()
