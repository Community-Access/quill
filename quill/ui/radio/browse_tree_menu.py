"""The browse tree's right-click menu, built away from the window.

Extracted from ``browse_tree_dialog`` when **Download...** arrived and that
module hit its GATE-11 ceiling -- and it belongs out here anyway: what a row
offers is a question about the *row*, not about the tree widget, and the answer
is now long enough to read on its own.

The menu is assembled per row rather than shown-and-greyed, with one exception
that matters: a row that cannot be downloaded simply has no *Download...* item,
but asking for one another way still says why. A missing item and a refusal are
different messages and both are needed -- an item that is always present and
usually disabled teaches people to stop reading the menu.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio.spotify_search import open_link_label


def show_for_event(dialog: Any, event: Any) -> None:
    wx = dialog._wx
    node = event.GetItem()
    dialog._tree.SelectItem(node)
    data = dialog._node_data(node)
    if data is None:
        return
    entries: list[tuple[str, Callable[[], None]]] = []
    station = data.get("station")
    if station is not None:
        playing = dialog._is_playing(station)
        saved = dialog._favorites.contains(station)
        entries = [
            ("&Stop" if playing else "&Play", dialog._play_selected),
            (
                "Remove from &Favorites" if saved else "Add to &Favorites",
                dialog._toggle_favorite,
            ),
            ("&Copy Stream Link", lambda: dialog._copy_text(station.stream_url)),
        ]
        if station.homepage:
            # A saved Spotify favorite says "Open in Spotify": for a free
            # account that link is how the track actually plays, not a
            # footnote about the station's website.
            entries.append((
                open_link_label(station),
                lambda: dialog._open_url(station.homepage),
            ))
        # Offered only where it can work -- a live station has no file to
        # save, and a source whose terms do not allow it is not guessed at.
        # The refusal is still spoken if the command is reached elsewhere.
        from quill.ui.radio import download_command

        if download_command.can_download(station):
            # The download host is the app shell, so the transfer joins the one
            # queue View > Downloads watches and outlives this window.
            host = getattr(dialog, "_download_host", dialog)
            entries.append((
                "&Download...",
                lambda s=station, h=host: download_command.download_station(h, s),
            ))
        if dialog._on_report_bad_station is not None:
            entries.append((
                "Report &Bad Station...",
                lambda s=station: dialog._on_report_bad_station(s),
            ))
    elif dialog._is_playable(data):
        entries = [("&Play", dialog._play_selected), ("Add to &Favorites", dialog._toggle_favorite)]
    elif dialog._is_folder_data(data):
        entries = [
            ("&Open", lambda: dialog._tree.Expand(node)),
            ("&Refresh", dialog._refresh_selected),
            ("Add All Stations to &Favorites", lambda: dialog._favorite_folder(node)),
        ]
        # A book is a folder of chapters, so "download this book" is a
        # folder action. Offered only when the folder is already open and
        # holds something savable -- a folder nobody has expanded has no
        # chapters to count, and fetching them to find out would make a
        # context menu do a network request.
        from quill.ui.radio import download_command

        chapters = dialog._loaded_stations_under(node)
        savable = [row for row in chapters if download_command.can_download(row)]
        if savable:
            label = dialog._tree.GetItemText(node)
            host = getattr(dialog, "_download_host", dialog)
            entries.append((
                f"&Download All {len(savable)} Files...",
                lambda rows=savable, name=label, h=host: download_command.download_book(
                    h, rows, title=name
                ),
            ))
    if not entries:
        return
    menu = wx.Menu()
    id_refs = []
    for label, handler in entries:
        item_id = wx.NewIdRef()
        id_refs.append(item_id)
        menu.Append(item_id, label)
        menu.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=item_id)
    # A SEPARATE attribute: assigning dialog._menu_id_refs here would drop the
    # menu-bar Close id ref pinned in it, re-exposing the id-reuse bug where
    # a random menu item closes the window.
    dialog._context_menu_id_refs = id_refs  # pinned while the popup can fire
    dialog._tree.PopupMenu(menu)
    menu.Destroy()
