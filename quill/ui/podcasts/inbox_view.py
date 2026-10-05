"""The Inbox laid out folders first (View > Inbox Layout; Preferences).

Folder rows lead the list -- "News, folder, 5 in the Inbox" -- and Enter on one
shows just that folder's Inbox episodes in place, the way Enter on a playlist
does; Backspace comes back to the folder row. With "Folders only", the episodes
from podcasts in no folder get a folder row of their own, so nothing in the
Inbox is ever out of reach. The plan is :func:`library_view.inbox_rows`.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts import library_view


def fill_inbox(host: Any, pairs: list[tuple[Any, Any]]) -> None:
    """Fill the list for the Inbox place, as laid out."""
    library = host._podcast_library
    rows = library_view.inbox_rows(library, pairs)
    lead = [(row.kind, row.folder_id, row.label) for row in rows if row.kind == "inbox_folder"]
    loose = [row.pair for row in rows if row.kind == "episode" and row.pair is not None]
    host._fill_episodes_from_pairs(loose, lead_rows=lead)


def open_inbox_folder(host: Any, folder_id: str, *, keep: Any = None) -> None:
    """Enter on an Inbox folder row: that folder's Inbox episodes, in place."""
    from quill.core.podcasts.virtual_views import virtual_view_pairs

    library = host._podcast_library
    pairs = library_view.inbox_folder_pairs(
        library, list(virtual_view_pairs(library, "inbox")), folder_id
    )
    host._place_opened_inbox_folder = folder_id
    pane = host._content
    pane.show(pane.LIST)
    host._fill_episodes_from_pairs(pairs)
    host._select_list_key(keep) or host._select_list_row(0)
    folder = library.find_folder(folder_id)
    name = folder.name if folder is not None else library_view.NO_FOLDER_LABEL
    pane.set_heading(f"Inbox: {name} ({len(pairs)})" if pairs else f"Inbox: {name}")
    host._refresh_selection_buttons()
    host._refresh_notes_pane()
    pane.focus()
