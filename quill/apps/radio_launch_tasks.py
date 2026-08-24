"""Everything Quill Radio does *after* its window is up.

Five things happen at the end of a launch, and every one of them is deferred
through ``wx.CallAfter`` for the same reason: a launch is not the moment to
seize focus a screen reader has not settled on yet, and it is not the moment
to wait on a network. Doing them inline would make the window appear late and
speak over itself when it did.

They are ordered, and the order is the argument:

1. **The data folder**, if it moved at this launch, or looks in use on another
   computer. Spoken, because it is news about where things are rather than
   something to act on now.
2. **Media health**, when this installation has lost the engine that plays
   Ogg/Opus/HLS or the one that records. Spoken for the same reason, and
   silent on a healthy install by design (#259).
3. **The startup window**, whichever one the listener chose -- or none.
4. **The first-run flow**, modal, because on a genuinely first launch it is
   the whole content of the window and Skip leaves in one keystroke. It comes
   after the startup window so it opens over a settled app rather than racing
   one.
5. **The subscribed-feed check**, which is armed rather than run: the monitor
   has to exist before Preferences can re-apply its cadence.

Extracted from ``apps/radio.py`` under GATE-11.
"""

from __future__ import annotations

from typing import Any


def schedule(app: Any, wx: Any, *, safe_mode: bool = False) -> Any:
    """Queue the launch tasks and return the feed monitor the app must keep.

    The monitor is returned rather than stashed on *app* from here, so the
    frame's attribute is assigned where every other attribute of it is and a
    reader of ``__init__`` can still see what the app owns.
    """
    from quill.apps import radio_podcast_refresh
    from quill.apps.radio_startup_window import open_startup_window
    from quill.ui.data_folder_dialog import surface_data_folder_startup
    from quill.ui.radio.first_run_dialog import maybe_run_first_run
    from quill.ui.radio.media_preflight import surface_media_health_startup

    wx.CallAfter(surface_data_folder_startup, app)
    wx.CallAfter(surface_media_health_startup, app)
    wx.CallAfter(open_startup_window, app)
    wx.CallAfter(maybe_run_first_run, app)
    return radio_podcast_refresh.install(app, wx, safe_mode=safe_mode)
