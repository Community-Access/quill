"""The Playback-menu items that could not fit in ``apps/radio.py``.

``radio.py`` owns Quill Radio's menu bar and has been at its GATE-11 ceiling for
several releases, so each group of items that arrives lands in a module of its
own and the frame keeps one call site. This one holds two groups:

* the **video** items -- scrub, speed, chapters, transcript -- which a finished
  YouTube video has and a live broadcast does not (``radio_video_menu``);
* **Listening Statistics**, which is new.

Both return their menu ids so the frame can pin them: a wx id that is garbage
collected while its menu can still fire gets reused, and the observable symptom
is a random menu item doing somebody else's job.
"""

from __future__ import annotations

from typing import Any

__all__ = ["build_playback_extras"]


def build_playback_extras(app: Any, menu: Any, wx: Any) -> tuple[Any, ...]:
    """Append the video items and Listening Statistics. Returns the ids to pin."""
    from quill.apps.radio_video_menu import build_video_playback_items

    ids = tuple(build_video_playback_items(app, menu, wx))

    # How long you listened, to what, and in which network. Radio kept a
    # recently-played list and a song log and neither of them was *time*, so
    # the app could say what you had on and never how much of it.
    stats_id = wx.NewIdRef()
    # Not Ctrl+Shift+I (Video Information, three items above) and not
    # Ctrl+Shift+Y (Add from YouTube Playlist, on Station): a key claimed twice
    # means one of the pair silently never fires, which is worse than a menu
    # item with a less memorable key.
    menu.Append(stats_id, "Listening Stati&stics...\tCtrl+Shift+Q")

    def _open(_event: Any) -> None:
        from quill.ui.radio.stats_dialog import open_for_host

        open_for_host(app)

    app.frame.Bind(wx.EVT_MENU, _open, id=stats_id)
    return (*ids, stats_id)
