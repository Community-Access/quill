"""The Playback menu's time-shift rows: rewind, forward, live, and the songs.

Rewind, Forward and Back to Live moved here from ``radio_menu_bar.py``
(at its GATE-11 ceiling) when the song-mark commands joined them, so the
rows that move inside the live buffer are built in one place and sit
together on the menu.

The song rows -- Previous Song, Next Song, Which Song Is This, the four Save
commands and the station's own time-shift length -- are ideas from BlindRadio
by serrebidev (MIT); their bodies are in :mod:`quill.ui.radio.song_marks_ui`.

Keys (all in ``APP_KEYMAPS["radio"]``, so a rebinding shows in the label):
Alt+Shift+Left and Alt+Shift+Right step by song, the bigger brother of
Rewind and Forward on Ctrl+Shift+Left and Right; Alt+Shift+W is "where",
like the transport's Where Am I on Ctrl+Shift+W; the saves sit on
Ctrl+Alt+F5 to F8 in BlindRadio's order (all, previous, next, current); and
the per-station length is Alt+Shift+T, a once-in-a-while key (rule 9).
"""

from __future__ import annotations

from typing import Any

#: ``(label, command id, handler name in song_marks_ui)`` for the song rows.
SONG_ROWS: tuple[tuple[str, str, str], ...] = (
    ("Previous &Song", "radio.previous_song", "previous_song"),
    ("Ne&xt Song", "radio.next_song", "next_song"),
    ("W&hich Song Is This?", "radio.which_song", "which_song"),
)

SAVE_ROWS: tuple[tuple[str, str, str], ...] = (
    ("Save &This Song", "radio.save_current_song", "save_current"),
    ("Save the &Previous Song", "radio.save_previous_song", "save_previous"),
    ("Save the &Next Song", "radio.save_next_song", "save_next"),
    ("Save &All Songs in the Buffer", "radio.save_all_songs", "save_all"),
)

STATION_ROW = (
    "Time-Shift Length for This Statio&n...",
    "radio.station_timeshift",
    "choose_station_timeshift",
)


def append_items(app: Any, playback_menu: Any, wx: Any) -> list[Any]:
    """Append the time-shift rows to *playback_menu*. Returns every id to pin."""
    from quill.ui.radio import song_marks_ui

    ids: list[Any] = []

    def add(menu: Any, label: str, command_id: str, handler: Any) -> None:
        item_id = wx.NewIdRef()
        menu.Append(item_id, app._menu_label(label, command_id))
        app.frame.Bind(wx.EVT_MENU, lambda _e: handler(), id=item_id)
        ids.append(item_id)

    # Live DVR (mpv engine): pause is the Play/Stop item; these move within
    # the buffered live window.
    add(playback_menu, "Re&wind", "radio.rewind", lambda: app.radio_rewind())
    add(playback_menu, "&Forward", "radio.forward", lambda: app.radio_forward())
    add(playback_menu, "Back to &Live", "radio.jump_to_live", lambda: app.radio_jump_to_live())
    for label, command_id, name in SONG_ROWS:
        add(playback_menu, label, command_id, _bound(song_marks_ui, name, app))
    save_menu = wx.Menu()
    for label, command_id, name in SAVE_ROWS:
        add(save_menu, label, command_id, _bound(song_marks_ui, name, app))
    playback_menu.AppendSubMenu(save_menu, "Save Songs from the B&uffer")
    label, command_id, name = STATION_ROW
    add(playback_menu, label, command_id, _bound(song_marks_ui, name, app))
    return ids


def _bound(module: Any, name: str, app: Any) -> Any:
    handler = getattr(module, name)
    return lambda: handler(app)


__all__ = ["SAVE_ROWS", "SONG_ROWS", "STATION_ROW", "append_items"]
