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
    menu_bar.Append(own, "Now &Playing")
    if windows is not None:
        windows.install(frame, menu_bar)
    frame.SetMenuBar(menu_bar)
    keep = getattr(host, "_keep_menu_ids", None)
    if callable(keep):
        keep(close_id)
    if windows is not None:
        windows.register(frame, TITLE, focus=lambda: window._slider.SetFocus())
