"""Quill Radio's calendar surfaces, wired (section 6).

Four commands, one timer, and one menu block -- kept here rather than in
``radio.py``, which is at its GATE-11 ceiling and is not improved by knowing
how a schedule is opened.

The four are deliberately separate keys rather than one window with tabs:

* **ACB Media Schedule** is a place you go and browse.
* **What Is On Now** is a question you ask *without leaving what you are
  doing*, which is the whole reason it is a key and not a row in a window. It
  answers out loud, from the cache, in one sentence.
* **Upcoming** is what you have planned, which is a different question from
  what is broadcast.
* **Refresh the Schedule** is "no, really, go and look" -- added 2026-08-25,
  when the only route to a re-read was a button inside the window and the
  hour-long cache survived a restart, so relaunching the app was not the
  escape hatch everybody reasonably assumed it was.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def register(app: Any) -> None:
    """Register the three commands. Called where the other commands are."""
    commands: Any = app.commands
    commands.try_register(
        "radio.acb_calendar",
        "ACB Media Schedule...",
        lambda: open_calendar(app),
        feature_id="core.radio",
    )
    commands.try_register(
        "radio.on_now",
        "What Is On Now",
        lambda: announce_on_now(app),
        feature_id="core.radio",
    )
    commands.try_register(
        "radio.upcoming",
        "Upcoming...",
        lambda: open_upcoming(app),
        feature_id="core.radio",
    )
    commands.try_register(
        "radio.refresh_calendar",
        "Refresh the ACB Media Schedule",
        lambda: refresh_calendar(app),
        feature_id="core.radio",
    )


def append_menu_items(host: Any, menu: Any, wx: Any) -> tuple[Any, ...]:
    """Append the three items, bound to *host*. The caller pins the ids."""
    ids = []
    for label, command, handler in (
        ("ACB Media &Schedule...", "radio.acb_calendar", lambda: open_calendar(host)),
        ("What Is On &Now", "radio.on_now", lambda: announce_on_now(host)),
        ("&Upcoming...", "radio.upcoming", lambda: open_upcoming(host)),
        (
            "Re&fresh the Schedule",
            "radio.refresh_calendar",
            lambda: refresh_calendar(host),
        ),
    ):
        item_id = wx.NewIdRef()
        menu.Append(item_id, host._menu_label(label, command))
        host.frame.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=item_id)
        ids.append(item_id)
    host._keep_menu_ids(*ids)
    return tuple(ids)


def open_calendar(host: Any) -> None:
    from quill.ui.radio.calendar_dialog import show_calendar

    show_calendar(host)


def open_upcoming(host: Any) -> None:
    from quill.ui.radio.upcoming_dialog import show_upcoming

    show_upcoming(host)


def refresh_calendar(host: Any) -> None:
    """Re-pull ACB's schedule, whether or not the window is open.

    **A fourth item, because Refresh was only ever a button.** The schedule is
    cached for an hour, so a listener who knew ACB had moved a programme had
    exactly one way to say so: open the window, tab past ten buttons, press
    Refresh. Closing and reopening the app did not do it -- the cache outlived
    the process, which is what made "it will not refresh" the reported symptom
    (2026-08-25). A menu item with a key is the route that does not require
    already being somewhere.

    With the window open it reloads the window, so the rows on screen and the
    feed cannot disagree. With it closed it fetches quietly and says what came
    back, in the same sentence the window's summary line uses -- including the
    time it was pulled, which is the part that makes a second press
    answerable.
    """
    from datetime import timedelta

    from quill.core.radio import acb_calendar, calendar_actions
    from quill.ui.radio.calendar_dialog import reload_open

    if reload_open():
        return

    if bool(getattr(host, "_safe_mode", False)):
        # Safe Mode's promise is that nothing reaches out. Saying so beats a
        # Refresh that silently does nothing.
        host._announce("Safe Mode is on, so the schedule is not re-read from ACB.")
        return

    tasks = getattr(host, "_task_manager", None)

    def _work(**_kwargs: Any) -> str:
        events, age = acb_calendar.fetch_schedule(refresh=True)
        now = datetime.now(UTC)
        pulled_at = now - timedelta(seconds=age or 0.0)
        return calendar_actions.summarise_schedule(
            list(events), list(events), now, age, pulled_at=pulled_at
        )

    host._announce("Reading the ACB Media schedule again...")
    if tasks is None:
        host._announce(_work())
        return
    tasks.submit(
        "radio-acb-calendar-refresh",
        _work,
        on_success=lambda _op, said: host._announce(str(said)),
        on_failure=lambda _op, error: host._announce(
            f"The ACB Media schedule could not be read. {error}."
        ),
    )


def announce_on_now(host: Any) -> None:
    """Say what is on across every ACB channel, without opening anything.

    Off the UI thread, and from the cache when there is one -- the point of a
    key is that it answers *now*, and a key that spends four seconds on a feed
    before speaking is a key nobody presses twice.
    """
    from quill.core.radio import acb_calendar, calendar_actions

    tasks = getattr(host, "_task_manager", None)
    safe = bool(getattr(host, "_safe_mode", False))

    def _work(**_kwargs: Any) -> str:
        # No *when*: "on now" is always this month, which is the default.
        events, _age = acb_calendar.fetch_schedule(safe_mode=safe)
        return calendar_actions.on_now_sentence(
            acb_calendar.on_now(list(events), datetime.now(UTC))
        )

    if tasks is None:
        host._announce(_work())
        return
    tasks.submit(
        "radio-acb-on-now",
        _work,
        on_success=lambda _op, said: host._announce(str(said)),
        on_failure=lambda _op, error: host._announce(
            f"The ACB Media schedule could not be read. {error}."
        ),
    )


def install_reminders(app: Any, wx: Any) -> Any:
    """Start the reminder timer and check once at launch."""
    from quill.ui.radio.reminder_monitor import install

    return install(app, wx)


__all__ = [
    "announce_on_now",
    "append_menu_items",
    "install_reminders",
    "open_calendar",
    "open_upcoming",
    "refresh_calendar",
    "register",
]
