"""Station-menu "Export Favorites to Playlist..." action for Quill Radio (#1249).

Thin wx wiring over :func:`quill.core.radio.playlist_export.export_m3u`: a Save
file dialog, writing the playlist text, and announcing the result. Kept out of
radio.py so that at-budget module stays lean (mirrors :mod:`backup_ui`).

The host ``frame`` provides the app-shell contract already used across the radio
UI: ``frame.frame`` (the wx.Frame), ``frame._announce``, ``frame._show_message_box``,
and ``frame._radio_favorites``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def export_favorites_to_playlist(frame: Any) -> None:
    """Write the listener's favorite stations to an M3U playlist they choose."""
    import wx

    from quill.core.radio.playlist_export import export_m3u

    store = frame._radio_favorites
    favorites = store.favorites_in_display_order()
    playable = [f for f in favorites if (f.station.stream_url or "").strip()]
    if not playable:
        frame._show_message_box(
            "You have no favorite stations to export yet. Add some stations to "
            "your favorites first.",
            "Export Favorites",
            wx.OK | wx.ICON_INFORMATION,
        )
        return

    with wx.FileDialog(
        frame.frame,
        "Export favorites to a playlist",
        defaultFile="quill-radio-favorites.m3u",
        wildcard="M3U playlist (*.m3u)|*.m3u|All files (*.*)|*.*",
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
    ) as file_dialog:
        if file_dialog.ShowModal() != wx.ID_OK:
            return
        destination = Path(file_dialog.GetPath())

    try:
        destination.write_text(export_m3u(playable), encoding="utf-8")
    except OSError as exc:
        frame._announce(f"Could not write the playlist: {exc}")
        return
    plural = "station" if len(playable) == 1 else "stations"
    frame._announce(f"Exported {len(playable)} {plural} to {destination.name}.")
