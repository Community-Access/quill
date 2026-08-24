"""Quill Radio's subscribed-feed check, installed on the app frame.

The monitor itself is :mod:`quill.ui.radio.podcast_refresh`; this is the three
lines of lifecycle that connect it to a running app, extracted under GATE-11.

They are three lines that each answer a question, which is why they are worth
naming rather than inlining:

* **Constructed at launch, not on first use** -- Preferences has to be able to
  re-apply the cadence the moment it is saved, and it can only do that to a
  monitor that already exists.
* **Started deferred** -- a launch that spends four seconds on feeds is a
  launch a screen-reader user spends waiting, and the at-launch check is quiet
  when it finds nothing because a launch is not the moment to be told that
  nothing happened.
* **Stopped on shutdown** -- a ``wx.Timer`` still running when its frame goes
  is a timer that can fire into a destroyed window.
"""

from __future__ import annotations

from typing import Any


def install(app: Any, wx: Any, *, safe_mode: bool = False) -> Any:
    """Build the monitor, apply the stored cadence, and arm the launch check."""
    from quill.ui.radio.podcast_refresh import PodcastRefreshMonitor

    monitor = PodcastRefreshMonitor(
        app.frame,
        history_provider=lambda: app._radio_history,
        announce=app._announce,
        task_manager=app._task_manager,
        safe_mode=safe_mode,
        wx=wx,
    )
    monitor.apply()
    wx.CallAfter(monitor.start_if_asked_at_launch)
    return monitor


def reapply(app: Any) -> str:
    """Re-read the cadence after Preferences is saved; returns what to say.

    Returns the policy sentence rather than announcing it, so the caller can
    fold it into whatever else the save is reporting instead of speaking twice.
    """
    monitor = getattr(app, "_podcast_refresh_monitor", None)
    if monitor is None:
        return ""
    monitor.apply()
    return str(monitor.describe())
