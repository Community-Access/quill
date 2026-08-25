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
6. **Reminders**, armed the same way and for the same reason -- plus one look
   straight away, which is what makes a reminder that came due while the app
   was closed still get said.

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
    # 6. **Reminders**, armed here for the same reason the feed check is: the
    #    timer has to exist before anything can set one, and its first look is
    #    what makes a reminder missed while the app was closed still speak.
    from quill.ui.radio import calendar_wiring

    app._reminder_monitor = calendar_wiring.install_reminders(app, wx)
    return radio_podcast_refresh.install(app, wx, safe_mode=safe_mode)


def register_surfaces(app: Any) -> None:
    """Register the surfaces that are neither menus nor launch tasks.

    Bookmarks (4.3) and the ACB Media schedule (section 6) each need two
    things done at the same moment -- commands registered, and the app told
    what it plays or can reopen -- and both have to happen after the command
    registry exists. One call because "which extra surfaces does Quill Radio
    have?" should have one answer in one place, and because ``radio.py`` is at
    its GATE-11 ceiling and is not improved by knowing either answer.
    """
    from quill.ui.radio import bookmarks_wiring, calendar_wiring

    bookmarks_wiring.register(app)
    calendar_wiring.register(app)


def append_calendar_menu(app: Any, menu: Any, wx: Any) -> None:
    """The ACB Media schedule's three items, fenced by a separator.

    **On the Community menu** since 2026-08-24. They were on Station, on the
    argument that a schedule is about what is *on*; but Station is the menu of
    everything this app can tune, and it had grown past twenty items, while the
    Community menu is precisely "places this community already goes, brought
    inside the app" -- which is what an ACB Media schedule is. It now sits
    beside ACB Community Events, where somebody looking for either will find
    both.

    The separator is only added when the menu already has something above,
    so a profile with the ADP assistant turned off gets a Community menu that
    opens on the schedule rather than on a rule.
    """
    from quill.ui.radio import acb_podcasts_wiring, calendar_wiring, community_picks_wiring

    if menu.GetMenuItemCount():
        menu.AppendSeparator()
    calendar_wiring.append_menu_items(app, menu, wx)
    # Beside the schedule, because they are the same question asked of the same
    # broadcaster: what is on live, and what can I keep. Both are "places this
    # community already goes, brought inside the app".
    acb_podcasts_wiring.append_menu_item(app, menu, wx)
    # The wider curated list, and the way to add to it. Last, because ACB is
    # what most people came for and the general list is the "what else?".
    menu.AppendSeparator()
    community_picks_wiring.append_menu_items(app, menu, wx)
