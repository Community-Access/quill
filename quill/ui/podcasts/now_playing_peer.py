"""Install the Now Playing window in the host's shared window navigation."""

from __future__ import annotations

from typing import Any

import wx

from quill.ui.podcasts.now_playing_layout import TITLE


def _install_peer(host: Any, window: Any) -> None:
    """Add the peer's own Close menu, shared Window menu, and registry entry."""
    windows = getattr(host, "_windows", None)
    frame = window.frame
    menu_bar = wx.MenuBar()
    own = wx.Menu()
    close_id = wx.NewIdRef()
    own.Append(close_id, "&Close\tCtrl+W")
    frame.Bind(wx.EVT_MENU, lambda _e: frame.Close(), id=close_id)
    # Here as well as on the main window's Episode menu: a chapter chosen in
    # this window is a jump, and the main bar's keys do not reach it (FUX-01).
    back_id = wx.NewIdRef()
    own.Append(back_id, "&Back to Where I Was\tAlt+Left")
    frame.Bind(wx.EVT_MENU, lambda _e: host.podcast_back_to_where_i_was(), id=back_id)
    # Where am I and how long is left, from the player itself: the main bar's
    # keys do not reach this window, and here is where they are wanted most.
    where_id, left_id = wx.NewIdRef(), wx.NewIdRef()
    if callable(getattr(host, "_menu_label", None)):
        rows = (
            (where_id, host._menu_label("&Where Am I?", "podcasts.where_am_i"), "say_where_am_i"),
            (
                left_id,
                host._menu_label("Time &Remaining", "podcasts.time_remaining"),
                "say_time_remaining",
            ),
        )
        for item_id, title, verb in rows:
            if callable(getattr(host, verb, None)):
                own.Append(item_id, title)
                frame.Bind(wx.EVT_MENU, lambda _e, v=verb: getattr(host, v)(), id=item_id)
    menu_bar.Append(own, "Now &Playing")
    if windows is not None:
        windows.install(frame, menu_bar)
    frame.SetMenuBar(menu_bar)
    keep = getattr(host, "_keep_menu_ids", None)
    if callable(keep):
        keep(close_id, back_id, where_id, left_id)
    if windows is not None:
        # on_show: Ctrl+2, Ctrl+Tab and the Window menu show this hidden window
        # without its own show(), which is what loads the episode playing now
        # and starts the clock; without it the window came back empty (Chris).
        windows.register(
            frame,
            TITLE,
            focus=lambda: window._slider.SetFocus(),
            on_show=lambda: window.show(focus=False),
        )
