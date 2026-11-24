"""The timeline refreshes without moving the reader (FUX-06).

Every refresh used to be a whole scope load: clear the list, fill it, select
the saved row, say "Home. 120 items, 14 unread." -- every 30 seconds when the
scheduler published, after every manual refresh, after every post. Selecting
the row again also marked it read, and a post that had gone sent the reader to
the first unread one, not its neighbour. New posts jumped in at the top.

Now a refresh changes the list row by row around the reader's post, which
stays the same row: selected, focused, on the same line, not re-read and not
re-marked. New posts are held back and counted; they join the list when the
reader asks (F5, Refresh). A post that has gone from the store is said once,
and the reader lands on the post that took its place. A post that only left
the scope because it is now read (in Unread) stays where the reader is.
"""

from __future__ import annotations

from typing import Any

from quill.core.list_follow import change_rows, gone_sentence, land
from quill.ui.list_stay_still import (
    NO_ANCHOR,
    capture_report,
    restore_report,
    say_when_settled,
)

__all__ = ["refresh_in_place", "is_followable", "held_sentence"]


def is_followable(scope: str) -> bool:
    """Scopes whose rows are posts, refreshed in place (not publishing or GitHub)."""
    return not scope.startswith(("pub:", "gh:"))


def held_sentence(count: int, key: str = "") -> str:
    """Said once when new posts are waiting behind the reader's list."""
    noun = "post" if count == 1 else "posts"
    how = f"Press {key} to show them" if key else "Refresh to show them"
    return f"{count} new {noun}. {how}."


def _merged(frame: Any, fresh: list[Any], show_arrivals: bool, reader: Any) -> list[Any]:
    """The posts to show: the fresh ones the reader already had (and, when
    asked, the arrivals), with the reader's own post kept in place when it
    only left the scope by being read."""
    shown = {it.item_id: i for i, it in enumerate(frame._items)}
    items = [it for it in fresh if show_arrivals or it.item_id in shown]
    if reader is None or any(it.item_id == reader.item_id for it in items):
        return items
    if frame.store.get_item(reader.item_id) is None:
        return items  # really gone
    before = shown[reader.item_id]

    def _above(it: Any) -> bool:
        if it.item_id in shown:
            return shown[it.item_id] < before
        return bool(it.created_at >= reader.created_at)

    at = sum(1 for it in items if _above(it))
    return [*items[:at], reader, *items[at:]]


def refresh_in_place(frame: Any, wx: Any, *, show_arrivals: bool) -> int:
    """Refresh the current scope around the reader; the number of arrivals.

    With *show_arrivals* False the arrivals are held (``frame._held``) and
    the count is returned for the caller to say; with True they join.
    """
    fresh = frame._scope_items(frame.current_scope)
    old = list(frame._items)
    old_ids = [it.item_id for it in old]
    anchor = capture_report(frame.list)
    reader = old[anchor.index] if 0 <= anchor.index < len(old) else None
    arrivals = [it for it in fresh if it.item_id not in set(old_ids)]
    items = _merged(frame, fresh, show_arrivals, reader)
    frame._held = 0 if show_arrivals else len(arrivals)
    rows = frame._row_texts(items)

    def _write(row: int, new: int, *, inserted: bool) -> None:
        if inserted:
            frame.list.InsertItem(row, rows[new])
        # The reader's own row is not rewritten under them: a screen reader
        # speaks a name change on the focused row. Its bold (unread) still is.
        elif reader is None or items[new].item_id != reader.item_id:
            if frame.list.GetItemText(row) != rows[new]:
                frame.list.SetItemText(row, rows[new])
        frame._mark_unread_row(row, items[new])

    frame._following = True  # selection events below are not the reader's doing
    try:
        change_rows(
            old_ids,
            [it.item_id for it in items],
            delete=frame.list.DeleteItem,
            insert=lambda row, new: _write(row, new, inserted=True),
            update=lambda row, new: _write(row, new, inserted=False),
            pin=None if reader is None else reader.item_id,
        )
        frame._items = items
        if reader is not None and items:
            keys = [it.item_id for it in items]
            landing = land(keys, reader.item_id, anchor.index)
            restore_report(wx, frame.list, anchor, landing.index)
            if not landing.kept:
                say = frame.announcer.say
                author = reader.author_display or reader.author_handle or "someone"
                say_when_settled(wx, frame.list, say, gone_sentence(f"The post by {author}"))
        elif reader is None and items and show_arrivals:
            restore_report(wx, frame.list, NO_ANCHOR, 0)  # as a scope load does; no focus taken
    finally:
        frame._following = False
    return len(arrivals)
