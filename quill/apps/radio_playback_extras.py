"""The Playback-menu items that could not fit in ``apps/radio.py``.

``radio.py`` owns Quill Radio's menu bar and has been at its GATE-11 ceiling for
several releases, so each group of items that arrives lands in a module of its
own and the frame keeps one call site. This one holds two groups:

* the **video** items -- scrub, speed, chapters, transcript -- which a finished
  YouTube video has and a live broadcast does not (``radio_video_menu``);
* **Listening Statistics**, which is new;
* and **Identify This Song** (``ui/radio/song_identify_commands``).

Both return their menu ids so the frame can pin them: a wx id that is garbage
collected while its menu can still fire gets reused, and the observable symptom
is a random menu item doing somebody else's job.
"""

from __future__ import annotations

from typing import Any

__all__ = ["append_song_items", "build_playback_extras"]


def build_playback_extras(
    app: Any,
    menu: Any,
    wx: Any,
    audio_menu: Any = None,
    video_menu: Any = None,
    view_menu: Any = None,
) -> tuple[Any, ...]:
    """Append the video items and Listening Statistics. Returns the ids to pin.

    Since the 2026-08-21 three-way split the caller may hand in an Audio and a
    Video menu; each falls back to *menu* when absent, so a surface that has not
    split its menus keeps working unchanged. Listening Statistics goes to
    *view_menu* when one is supplied -- it is a report about past listening, not
    a control over present listening, and View is where the other reports are.
    """
    from quill.apps.radio_video_menu import build_video_playback_items

    ids = tuple(
        build_video_playback_items(app, menu, wx, audio_menu=audio_menu, video_menu=video_menu)
    )

    # How long you listened, to what, and in which network. Radio kept a
    # recently-played list and a song log and neither of them was *time*, so
    # the app could say what you had on and never how much of it.
    stats_id = wx.NewIdRef()
    # Not Ctrl+Shift+I (Video Information, three items above) and not
    # Ctrl+Shift+Y (Add from YouTube Playlist, on Station): a key claimed twice
    # means one of the pair silently never fires, which is worse than a menu
    # item with a less memorable key.
    # A report about past listening, not a control over present listening, so
    # it belongs in View with the other reports rather than in Playback with the
    # transport. Falls back to *menu* for a caller that has not split its menus.
    stats_home = view_menu if view_menu is not None else menu
    stats_home.Append(stats_id, "Listening Stati&stics...\tCtrl+Shift+Q")

    def _open(_event: Any) -> None:
        from quill.ui.radio.stats_dialog import open_for_host

        open_for_host(app)

    app.frame.Bind(wx.EVT_MENU, _open, id=stats_id)
    # Identify This Song (AcoustID): a question about what is playing, so it
    # sits on Playback with What's Playing rather than with the reports.
    from quill.ui.radio import song_identify_commands

    identify_id = song_identify_commands.append_menu_item(app, menu, wx)
    return (*ids, stats_id, identify_id)


def append_song_items(app: Any, menu: Any, wx: Any) -> tuple[Any, ...]:
    """Append Song History and Lyrics to the Playback menu. Returns the ids to pin.

    Together because they are the two questions about the song itself -- what
    was that, and what are the words -- and because ``radio_menu_bar`` is at its
    GATE-11 ceiling, so the second one could not join the first there.
    """
    # Ctrl+Shift+H is free in the standalone app; inside full QUILL the same
    # command ships unbound because there Ctrl+Shift+H is Replace All.
    song_history_id = wx.NewIdRef()
    menu.Append(song_history_id, app._menu_label("&Song History...", "radio.song_history"))
    app.frame.Bind(wx.EVT_MENU, lambda _e: app.radio_song_history(), id=song_history_id)
    # The words of the song on the air, from LRCLIB, only when asked
    # (quill.ui.radio.lyrics_commands). Ctrl+Alt+B, not the Ctrl+Alt+L the plan
    # named: Ctrl+Alt+L is Resume Last Station on Launch on the Station menu,
    # and B is the one Ctrl+Alt letter this window has left (app_keymaps.py).
    lyrics_id = wx.NewIdRef()
    menu.Append(lyrics_id, app._menu_label("L&yrics...", "radio.lyrics"))

    def _lyrics(_event: Any) -> None:
        from quill.ui.radio import lyrics_commands

        lyrics_commands.lyrics_for_playing(app)

    app.frame.Bind(wx.EVT_MENU, _lyrics, id=lyrics_id)
    return (song_history_id, lyrics_id)
