"""The Station-menu rows for Play Random Station and Play Random Favorite.

Extracted from ``radio_menu_bar.py`` under GATE-11 (extract, never rebaseline).
Wiring only: the choosing is ``core/radio/play_random.py`` and the playing is
``ui/radio/play_random_ui.py``. The rows sit directly after Play Last Station,
because all three answer "put something on without browsing", and each takes its
key from the app keymap so the menu shows what is actually bound.
"""

from __future__ import annotations

from typing import Any


def build_random_items(app: Any, station_menu: Any, wx: Any) -> tuple[Any, ...]:
    """Append the two Play Random rows to *station_menu*, bound to *app*.

    Returns the id refs, which the caller must pin: a menu id ref that is
    garbage-collected can be reissued to a different item.
    """
    station_id, favorite_id = wx.NewIdRef(), wx.NewIdRef()
    station_menu.Append(station_id, app._menu_label("Play Rando&m Station", "radio.play_random"))
    station_menu.Append(
        favorite_id, app._menu_label("Play Random Favorite&s", "radio.play_random_favorite")
    )
    app.frame.Bind(wx.EVT_MENU, lambda _e: app.radio_play_random(), id=station_id)
    app.frame.Bind(wx.EVT_MENU, lambda _e: app.radio_play_random_favorite(), id=favorite_id)
    return (station_id, favorite_id)
