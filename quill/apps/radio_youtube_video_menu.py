"""Video > YouTube: Live Chat, YouTube Video, Skip Sponsor Segments, filtered search.

A submenu rather than four more rows on the Video menu, which already holds the
picture commands; everything in it is about the YouTube video that is playing
(or, for the search, finding the next one). Extracted beside
:mod:`quill.apps.radio_video_menu` (GATE-11) and called from it.

Keys are the Ctrl+Alt+Shift digit row, the last free row on Quill Radio's bar
(see ``app_keymaps``); digits, so no mnemonic is pretended -- Alt+D, Y and the
item's letter are the one-key-at-a-time route.
"""

from __future__ import annotations

from typing import Any


def add_youtube_video_items(app: Any, video_menu: Any, wx: Any) -> tuple[Any, ...]:
    """Append the YouTube submenu to *video_menu*; return the ids to pin."""
    from quill.ui.radio import (
        youtube_live_chat_ui,
        youtube_search_filters_ui,
        youtube_sponsorblock_ui,
        youtube_video_window,
    )

    submenu = wx.Menu()
    rows = (
        ("&Live Chat...", "radio.youtube_live_chat", youtube_live_chat_ui.open_for_playing),
        ("YouTube &Video...", "radio.youtube_video", youtube_video_window.open_for_playing),
        (
            "Skip &Sponsor Segments...",
            "radio.youtube_sponsorblock",
            youtube_sponsorblock_ui.open_settings,
        ),
        (
            "Search YouTube with &Filters...",
            "radio.youtube_search_filters",
            youtube_search_filters_ui.search_with_filters,
        ),
    )
    ids = []
    for label, command_id, handler in rows:
        item_id = wx.NewIdRef()
        submenu.Append(item_id, app._menu_label(label, command_id))
        app.frame.Bind(wx.EVT_MENU, lambda _e, h=handler: h(app), id=item_id)
        ids.append(item_id)
    video_menu.AppendSubMenu(submenu, "&YouTube")
    # Begin skipping again at start-up if the listener left it on.
    youtube_sponsorblock_ui.start_if_on(app)
    return tuple(ids)


__all__ = ["add_youtube_video_items"]
