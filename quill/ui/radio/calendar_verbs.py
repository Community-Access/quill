"""What each calendar verb actually does (6.4, 6.5).

Split from the window under GATE-11, and it is a real seam: the window owns
*which* verbs a row has and how they read; this owns what happens when one
runs. They change for different reasons -- a new verb is a menu question, and
"Schedule a Recording should pre-fill the end time" is not.

The rule they share: **a verb that cannot finish says why, and changes
nothing.** Every one of these can meet a schedule that has moved on -- a
channel that no longer exists, a programme that ended while the window was
open -- and the answer is always a sentence rather than an exception or a
silent no-op.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from quill.core.radio import acb_calendar, calendar_actions


def run(host: Any, window: Any, action_id: str, event: Any) -> None:
    """Dispatch one verb. Never raises into the window."""
    handlers = {
        calendar_actions.PLAY: _play,
        calendar_actions.RECORD: _record,
        calendar_actions.REMIND: _remind,
        calendar_actions.UNREMIND: _unremind,
        calendar_actions.QUEUE: _queue,
        calendar_actions.COPY: _copy,
        calendar_actions.DETAILS: _details,
    }
    handler = handlers.get(action_id)
    if handler is None:
        return
    try:
        handler(host, window, event)
    except Exception as error:  # noqa: BLE001 - reported, never raised at a menu
        host._announce(f"That could not be done: {error}.")


def playing_stream_name(host: Any) -> str:
    """The ACB channel the player is on right now, or ``""``.

    The window asks this to label its Play button, and :func:`_play` asks it
    again to decide what pressing that button does. One function so the label
    and the action can never disagree -- a button that says Stop and restarts
    is worse than one that only ever said Play.
    """
    controller = getattr(host, "_radio_controller", None)
    state = getattr(controller, "state", None)
    station = getattr(state, "station", None)
    name = str(getattr(station, "name", "") or "")
    if not name:
        return ""
    # ACTIVE_STATES, not RUNNING_STATES (fixed 2026-08-25). RUNNING is PLAYING
    # and BUFFERING only, so for the second or two a stream spends CONNECTING
    # this said "nothing is on" -- and the button, which is only relabelled
    # when something happens, then sat reading Play for the whole broadcast
    # (reported: *"the play button label does not become stop when Play is
    # pressed on the community screen"*). Every other surface that flips a
    # Play button -- the Favorites Manager, Browse Stations, the station
    # browser -- asks ACTIVE_STATES, which is the set that means "on the air,
    # or on its way to it". This one asked a narrower question and got a
    # narrower answer.
    from quill.ui.radio.playback_state import ACTIVE_STATES, RadioPlayerState

    current = getattr(state, "state", None)
    if current not in (ACTIVE_STATES | {RadioPlayerState.PAUSED}):
        return ""
    return name


def _play(host: Any, _window: Any, event: Any) -> None:
    """Tune in to the programme's channel -- or stop it, if it is already on.

    The *channel*, not the programme: a live stream has one thing on it at a
    time, and what that is depends on when you arrive. Playing a Thursday show
    on Tuesday is not a thing the medium can do, and the announcement says
    which it did.

    **Pressing it on the channel you are already listening to stops.** It used
    to call ``play_station`` regardless, which tore the stream down and rebuilt
    it: a few seconds of silence, the same audio back, and no way to stop from
    this window at all (reported 2026-08-24).

    Neither branch re-faces the window any more: :meth:`_invoke` syncs after
    *every* verb, because "this verb changed what this row can do" is true of
    all of them and the stop branch doing it alone is how Play came to be the
    one that did not (2026-08-25).
    """
    station = acb_calendar.station_for(event)
    if station is None:
        host._announce("That programme does not say which channel it is on.")
        return
    controller = getattr(host, "_radio_controller", None)
    if controller is None:
        host._announce("Nothing here can play that.")
        return
    if acb_calendar.same_stream(playing_stream_name(host), station.name):
        controller.stop()
        host._announce(f"Stopped {station.name}.")
        return
    controller.play_station(station)
    now = datetime.now(UTC)
    if event.overlaps(now):
        host._announce(f"Playing {station.name}. {event.summary} is on now.")
    else:
        when = calendar_actions.clock(event.start)
        host._announce(
            f"Playing {station.name}. {event.summary} is not on yet -- it starts at {when}."
        )


def _record(host: Any, window: Any, event: Any) -> None:
    """Schedule a one-off recording of this programme, after confirming it.

    Built here rather than by opening Schedule Recording pre-filled: the
    calendar already knows the channel, the date, the local start time and the
    length, which is every field that window would ask for. Handing somebody a
    form they only have to press OK on is a form.

    Confirmed first, because a recording is disk, a wake-up and a block of
    time -- and the confirmation is where those four facts get read back, which
    is also how a wrong one gets caught before it runs.
    """
    from quill.core.paths import app_data_dir
    from quill.core.radio.recording_schedule import (
        RecordingScheduleEntry,
        load_schedule,
        new_id,
        save_schedule,
    )
    from quill.ui.dialog_contract import show_message_box

    station = acb_calendar.station_for(event)
    if station is None:
        host._announce("That programme does not say which channel it is on.")
        return
    local = event.start.astimezone()
    minutes = int(event.duration.total_seconds() // 60) if event.duration else 60
    minutes = max(1, min(minutes, 24 * 60))
    question = (
        f"Record {event.summary} from {station.name}?\n\n"
        f"{calendar_actions.day_label(event.start, 1).split(',')[0]} at "
        f"{calendar_actions.clock(event.start)}, for {minutes} minute(s)."
    )
    import wx

    answer = show_message_box(
        question,
        "Schedule a Recording",
        wx.YES_NO | wx.ICON_QUESTION,
        window.dialog,
        announce=host._announce,
    )
    if answer != wx.YES:
        return
    data_dir = app_data_dir()
    entries = load_schedule(data_dir)
    entries.append(
        RecordingScheduleEntry(
            id=new_id(),
            station_name=station.name,
            stream_url=station.stream_url,
            recurrence="once",
            # Local wall clock with an empty timezone means "this machine's
            # time", which is what the listener just read in the confirmation.
            run_at=local.strftime("%Y-%m-%dT%H:%M"),
            duration_minutes=minutes,
        )
    )
    save_schedule(data_dir, entries)
    host._announce(
        f"Scheduled a recording of {event.summary} on {station.name}, "
        f"{calendar_actions.clock(event.start)}, for {minutes} minutes."
    )


def _remind(host: Any, window: Any, event: Any) -> None:
    """Ask for the details, then set it.

    The same dialog every other row uses (7.1-7.3), rather than the lead-time
    list this shipped with: a programme reminder and a station reminder are the
    same record, and two dialogs would have been two places for the note field
    and the priority to be missing from one of them.
    """
    from quill.core.radio import reminders
    from quill.ui.radio import reminder_dialog

    reminder = reminder_dialog.ask(
        host,
        window.dialog,
        title=event.summary,
        kind=reminders.KIND_EVENT,
        target=event.uid,
        starts_at=event.start,
        note=acb_calendar.stream_for(event),
    )
    if reminder is None:
        return
    window._sync()
    host._announce(reminder_dialog.spoken_confirmation(reminder))


def _unremind(host: Any, window: Any, event: Any) -> None:
    from quill.core.paths import app_data_dir
    from quill.core.radio import reminders

    existing = reminders.find_for_target(app_data_dir(), reminders.KIND_EVENT, event.uid)
    if existing is None:
        host._announce("There is no reminder on that programme.")
        return
    reminders.remove_reminder(app_data_dir(), existing.reminder_id)
    window._sync()
    host._announce(f"Reminder removed from {event.summary}.")


def _queue(host: Any, _window: Any, event: Any) -> None:
    """Put the channel in the Play Queue.

    The channel again, and the announcement says so: a queued live stream
    plays whatever is on when the queue reaches it, and somebody who thought
    they had queued Thursday's programme would find that out at the worst
    moment.
    """
    station = acb_calendar.station_for(event)
    if station is None:
        host._announce("That programme does not say which channel it is on.")
        return
    enqueue = getattr(host, "radio_add_to_queue", None) or getattr(host, "add_to_play_queue", None)
    if not callable(enqueue):
        host._announce("There is no play queue here.")
        return
    enqueue(station)
    host._announce(
        f"Added {station.name} to the Play Queue. A live channel plays whatever is "
        "on when the queue reaches it."
    )


def _copy(host: Any, _window: Any, event: Any) -> None:
    text = calendar_actions.details_text(event)
    copier = getattr(host, "_copy_text", None)
    if callable(copier):
        copier(text)
    else:  # pragma: no cover - every app on the shell has _copy_text
        import wx

        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
            finally:
                wx.TheClipboard.Close()
    host._announce(f"Copied the details for {event.summary}.")


def _details(host: Any, window: Any, event: Any) -> None:
    """Read the programme's own description.

    A message box rather than a bespoke window: it is a paragraph, it is
    read once, and it needs nothing but OK.
    """
    body = calendar_actions.details_text(event)
    shower = getattr(host, "_show_message_box", None)
    if callable(shower):
        shower(body, event.summary)
        return
    import wx

    wx.MessageBox(  # MSGBOX-OK: parented read-only detail for one calendar row
        body, event.summary, wx.OK | wx.ICON_INFORMATION, window.dialog
    )


def export_schedule(host: Any, parent: Any, events: list[Any]) -> None:
    """Write what is listed to Markdown.

    What is *listed* -- filtered by channel, date and the search box -- because
    what somebody exports is what they are looking at. Exporting the whole
    published schedule from a filtered window would be the app answering a
    question nobody asked.
    """
    from pathlib import Path

    import wx

    if not events:
        host._announce("There is nothing listed to export.")
        return
    ordered = sorted(events, key=lambda event: event.start)
    first = ordered[0].start.astimezone()
    default = f"acb-media-{first.strftime('%Y-%m-%d')}.md"
    with wx.FileDialog(
        parent,
        message="Export this schedule",
        defaultFile=default,
        wildcard="Markdown (*.md)|*.md|Text (*.txt)|*.txt|All files (*.*)|*.*",
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
    ) as chooser:
        if chooser.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return
        destination = Path(chooser.GetPath())
    spread = calendar_actions.published_range(ordered)
    heading = f"ACB Media schedule, {spread}" if spread else "ACB Media schedule"
    try:
        destination.write_text(
            calendar_actions.schedule_markdown(ordered, heading=heading), encoding="utf-8"
        )
    except OSError as error:
        host._announce(f"The schedule could not be exported. {error}.")
        return
    host._announce(f"Exported {len(ordered)} programme(s) to {destination.name}.")


__all__ = ["export_schedule", "playing_stream_name", "run"]
