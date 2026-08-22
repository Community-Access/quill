"""The Audio menu's three remembered preferences.

Split out of :mod:`quill.apps.radio` under GATE-11 (extract, never rebaseline)
when one Playback menu of 39 items became Playback, Audio and Video on
2026-08-21. These three are the settings half of the Audio menu -- what the app
remembers about how you like it to sound -- as opposed to the transport half
(mute, volume, boost) that acts on this moment.

Each is a check item whose state is read back from ``RadioHistory`` as it is
built, so a menu opened after a change made elsewhere shows the truth rather
than whatever it was told at construction.
"""

from __future__ import annotations

from typing import Any


def build_preferences(app: Any, audio_menu: Any, wx: Any) -> Any:
    """Append Use One Volume, Forget Station Volumes and Announce Track Titles.

    Returns the one id that is not stored on *app*, so the caller can pin it:
    wx frees an unreferenced NewIdRef, and a freed id is a menu item that
    fires nothing.
    """
    app._global_volume_item_id = wx.NewIdRef()
    audio_menu.AppendCheckItem(
        app._global_volume_item_id,
        app._menu_label("Use One &Volume for All Stations", "radio.toggle_global_volume"),
    )
    audio_menu.Check(app._global_volume_item_id, app._radio_history.use_global_volume)
    app.frame.Bind(
        wx.EVT_MENU,
        lambda _e: app.radio_toggle_global_volume(),
        id=app._global_volume_item_id,
    )

    forget_volumes_id = wx.NewIdRef()
    audio_menu.Append(
        forget_volumes_id,
        app._menu_label("Forget Every Station's Own Volu&me...", "radio.forget_station_volumes"),
    )
    app.frame.Bind(wx.EVT_MENU, lambda _e: app.radio_forget_station_volumes(), id=forget_volumes_id)

    app._announce_titles_item_id = wx.NewIdRef()
    audio_menu.AppendCheckItem(
        app._announce_titles_item_id,
        app._menu_label("Announce Trac&k Titles", "radio.toggle_title_announcements"),
    )
    audio_menu.Check(app._announce_titles_item_id, app._radio_history.announce_track_titles)
    app.frame.Bind(
        wx.EVT_MENU,
        lambda _e: app.radio_toggle_title_announcements(),
        id=app._announce_titles_item_id,
    )
    return forget_volumes_id
