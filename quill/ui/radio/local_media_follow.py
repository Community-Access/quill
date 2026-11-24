"""Local Media's two lists, kept still while the library changes (FUX-06).

A folder scan, a tag read or another window changes the library while the
Local Media window is open. The lists change row by row, by identity: a file
added earlier in the playlist is inserted, it does not rewrite every row below
it with its neighbour's text, and the reader's row stays the same native item,
selected, focused and on the same line. Kept out of ``local_media_window`` so
that module stays under its size budget (GATE-11).
"""

from __future__ import annotations

from typing import Any

from quill.core.list_follow import change_rows, gone_sentence, land
from quill.ui.list_stay_still import RowAnchor, refill_listbox, restore_report, say_when_settled
from quill.ui.media.list_columns_view import fill_row, set_row

__all__ = ["fill_playlists", "change_item_rows", "keep_reader"]


def fill_playlists(window: Any, labels: list[str], ids: list[str], wanted: str) -> None:
    """The Playlists list, row by row, landing on *wanted* (or staying put)."""
    old = list(getattr(window, "_playlist_ids", []))
    if len(old) != window._playlists.GetCount():
        old = []  # never filled yet
        window._playlists.Clear()
    refill_listbox(window._playlists, old, ids, labels, wanted or None)
    window._playlist_ids = ids


def change_item_rows(
    window: Any, old_ids: list[int], items: list[Any], cells: list[dict[str, str]], pin: int | None
) -> None:
    """Make the Items list show *items*, touching only the rows that changed."""
    old_text = list(window._row_text)

    def _update(row: int, new: int) -> None:
        if row >= len(old_text) or old_text[row] != cells[new]:
            set_row(window._items, row, window._columns, cells[new])

    def _delete(row: int) -> None:
        window._items.DeleteItem(row)
        if row < len(old_text):
            del old_text[row]

    def _insert(row: int, new: int) -> None:
        fill_row(window._items, row, window._columns, cells[new])
        old_text.insert(row, cells[new])

    change_rows(
        [str(item_id) for item_id in old_ids],
        [str(item.id) for item in items],
        delete=_delete,
        insert=_insert,
        update=_update,
        pin=None if pin is None else str(pin),
    )


def keep_reader(
    window: Any,
    anchor: RowAnchor,
    focused: tuple[int, str] | None,
    rows: list[int],
    *,
    say_gone: bool,
) -> None:
    """The reader's rows still selected, the focused one on its line, no focus taken.

    When the file they were on has gone from the playlist through a change
    they did not make here, they land on the row that moved into its place,
    and hear why once the screen reader has read that row.
    """
    if focused is None:
        return
    keys = [str(item_id) for item_id in window._item_ids]
    landing = land(keys, str(focused[0]), anchor.index)
    if landing.index < 0:
        return
    also = [row for row in rows if row >= 0]
    restore_report(window._wx, window._items, anchor, landing.index, also=also)
    if not landing.kept and say_gone:
        from quill.ui.radio import local_media_ui as ui

        say = lambda text: ui.announce(window._host, text)  # noqa: E731
        say_when_settled(window._wx, window._items, say, gone_sentence(focused[1]))
