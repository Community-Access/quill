"""The Play Queue window follows the queue when it changes somewhere else (FUX-06).

The window is modal, but the app behind it keeps working: an episode finishes
and the next one is taken off the front of the queue, a feed refresh queues
what just arrived, a notification's Add to Queue appends. The window used to
know none of it. It kept showing the queue as it was when it opened, and every
row still pointed at a queue *position* -- so once the front item had gone,
"Remove" on the row the listener was reading took out the episode after it,
silently.

Now the window compares what it shows with the queue, by identity (show id and
episode guid), on a short timer and again before any verb reads the
selection. When they differ it redraws, and the rows the listener had selected
stay selected -- the same episodes, wherever they now sit -- with the caret on
the same one and on the same line of the screen. It says nothing: what arrived
was already said by whatever queued it ("3 new episodes in The Daily; 3 added
to the Play Queue."), and the reader says the row when it moves.
"""

from __future__ import annotations

from typing import Any

from quill.ui.list_stay_still import capture_listbox, restore_listbox

__all__ = ["WATCH_MS", "catch_up", "queue_keys", "start_watch"]

#: How often the open window looks. Comparing a few hundred pairs is nothing;
#: half a second is short enough that nobody acts on a stale row by hand.
WATCH_MS = 500


def queue_keys(library: Any) -> tuple[tuple[str, str], ...]:
    """The queue as identities, in play order."""
    return tuple((item.show_id, item.episode_guid) for item in library.queue)


def start_watch(dialog: Any) -> Any:
    """Look at the queue every :data:`WATCH_MS`; the caller stops the timer it returns.

    Started by ``show()`` around the modal loop and stopped before the window
    is destroyed -- a timer left running on a destroyed window fires into
    freed memory.
    """
    wx = dialog._wx
    window = dialog.dialog
    timer = wx.Timer(window)
    window.Bind(wx.EVT_TIMER, lambda _event: catch_up(dialog), timer)
    timer.Start(WATCH_MS)
    return timer


def _row_key(rows: list[tuple[int | None, str]], shown: tuple[Any, ...], row: int) -> Any:
    index, label = rows[row]
    if index is None:
        return ("group", label)
    return shown[index] if 0 <= index < len(shown) else None


def catch_up(dialog: Any) -> bool:
    """Redraw if the queue changed elsewhere, keeping the listener's rows. True if it did."""
    library = dialog._library
    keys = queue_keys(library)
    shown = getattr(dialog, "_shown_keys", keys)
    if keys == shown:
        return False
    box = dialog._list
    rows = list(getattr(dialog, "_rows", []))
    selections = sorted(row for row in box.GetSelections() if 0 <= row < len(rows))
    picked = [key for key in (_row_key(rows, shown, row) for row in selections) if key]
    caret_key = _row_key(rows, shown, selections[0]) if selections else None
    marked = dialog._marked_index
    marked_key = shown[marked] if marked is not None and 0 <= marked < len(shown) else None
    where = {key: index for index, key in enumerate(keys)}
    dialog._marked_index = where.get(marked_key) if marked_key is not None else None
    anchor = capture_listbox(box)
    box.Freeze()
    try:
        dialog._fill_rows()
        row_of: dict[Any, int] = {}
        for row, (index, label) in enumerate(dialog._rows):
            row_of[("group", label) if index is None else keys[index]] = row
        targets = [row_of[key] for key in picked if key in row_of]
        caret = row_of.get(caret_key, targets[0] if targets else -1)
        if not targets and anchor.index >= 0 and dialog._rows:
            # Everything selected left the queue: the row that moved into its
            # place, never the top (qc.md F-10).
            caret = min(anchor.index, len(dialog._rows) - 1)
            targets = [caret]
        restore_listbox(box, anchor, targets, caret)
    finally:
        box.Thaw()
    return True
