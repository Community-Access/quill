"""The Station menu's YouTube search and repair rows.

Extracted from :mod:`quill.apps.radio_menu_bar` (GATE-11: that module sits at
its ceiling) when Search YouTube... arrived. The two rows belong together:
both are about reaching YouTube at all -- one finds things on it, the other
repairs the helper that talks to it when YouTube changes.
"""

from __future__ import annotations

from typing import Any


def add_youtube_menu_items(app: Any, station_menu: Any, wx: Any) -> None:
    """Search YouTube... and Repair YouTube Support..., bound to *app*."""
    from quill.ui.radio import youtube_search_ui

    # Videos, playlists and channels, answered in Browse Stations. H, because
    # every other letter of "Search YouTube" is already another Station item's.
    search_id = wx.NewIdRef()
    station_menu.Append(search_id, app._menu_label("Searc&h YouTube...", "radio.search_youtube"))
    app.frame.Bind(wx.EVT_MENU, lambda _e: youtube_search_ui.search_youtube(app), id=search_id)
    # YouTube support is built in, so this is only ever needed when YouTube
    # changes how it serves audio and the bundled helper goes stale. It sits
    # next to the YouTube commands because that is where someone whose
    # YouTube links stopped working will look for it.
    update_id = wx.NewIdRef()
    station_menu.Append(update_id, "Repair YouTube S&upport...\tCtrl+Alt+Y")
    app.frame.Bind(wx.EVT_MENU, lambda _e: app.radio_update_youtube_support(), id=update_id)
    app._keep_menu_ids(search_id, update_id)
