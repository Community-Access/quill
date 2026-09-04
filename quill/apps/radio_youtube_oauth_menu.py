"""Station menu items for Connect YouTube Account (future.youtube_oauth).

Extracted from ``apps/radio.py`` (GATE-11 -- extract, never rebaseline) so
that module's menu build does not grow past its budget. Locked off in a
public build until this build's Google OAuth client is verified (see
``core/radio/youtube_oauth.py``); visible in a developer build for test-user
sign-in. Lives beside the Takeout import in the Station menu -- both end at
the same ChannelStore, so a listener finds either import path there.
"""

from __future__ import annotations

from typing import Any


def add_youtube_oauth_menu_items(host: Any, station_menu: Any, wx: Any) -> None:
    """Append Connect/Disconnect YouTube Account, when the flag and mode allow."""
    if not host.features.is_enabled("future.youtube_oauth") or host._safe_mode:
        return
    from quill.ui.radio.youtube_oauth_ui import (
        connect_youtube_account,
        disconnect_youtube_account,
    )

    connect_id = wx.NewIdRef()
    station_menu.Append(
        connect_id, host._menu_label("Co&nnect YouTube Account...", "radio.connect_youtube_account")
    )
    host.frame.Bind(wx.EVT_MENU, lambda _e: connect_youtube_account(host), id=connect_id)

    disconnect_id = wx.NewIdRef()
    station_menu.Append(
        disconnect_id,
        host._menu_label("Disconnect YouTube Accou&nt...", "radio.disconnect_youtube_account"),
    )
    host.frame.Bind(wx.EVT_MENU, lambda _e: disconnect_youtube_account(host), id=disconnect_id)
