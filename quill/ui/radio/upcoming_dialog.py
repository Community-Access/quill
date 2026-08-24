"""Upcoming: everything scheduled or reminded, across sources (6.7, 7.7).

Two features answer the same question -- *what has Quill Radio got planned?* --
and until now each answered only its own half. Scheduled recordings lived in
Schedule Recording; reminders lived nowhere, because there were none. Somebody
who set a recording on Tuesday and a reminder on Thursday had to open two
windows to find out what their week held.

So this window merges them, sorted by when, with the source on every row. That
is the whole idea, and the only thing it has to get right is that a row says
which kind it is: Dismiss on a reminder forgets a reminder, and Dismiss on a
recording would cancel a recording -- the same word, two very different
mornings.

Snooze, Dismiss and Go There are reminder verbs; a recording row offers Open in
Schedule Recording instead, because cancelling a recording belongs to the window
that made it and its confirmation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from quill.core.radio import reminders as rem
from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids

TITLE = "Upcoming"

#: Snooze steps, as ``(seconds, label)``. Short, because snooze is what you
#: press when you are busy *now* -- an hour's snooze is a dismissal wearing a
#: kinder name.
SNOOZE_CHOICES: tuple[tuple[int, str], ...] = (
    (300, "5 minutes"),
    (600, "10 minutes"),
    (1800, "30 minutes"),
)


def show_upcoming(host: Any) -> None:
    """Open the Upcoming window. Modal, house pattern."""
    import wx

    from quill.core.paths import app_data_dir

    data_dir = app_data_dir()
    rows: list[tuple[str, Any]] = []

    dialog = wx.Dialog(host.frame, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    dialog.SetSize(wx.Size(760, 460))
    root = wx.BoxSizer(wx.VERTICAL)

    summary = wx.StaticText(dialog, label="")
    root.Add(summary, 0, wx.ALL, 8)
    root.Add(wx.StaticText(dialog, label="&What is coming up:"), 0, wx.LEFT | wx.RIGHT, 8)
    listbox = wx.ListBox(dialog, style=wx.LB_SINGLE)
    described = (
        "Everything Quill Radio has planned -- reminders and scheduled "
        "recordings together, soonest first, with the kind on every row. "
        "Enter opens whatever the highlighted row is about."
    )
    listbox.SetName(described)
    listbox.SetHelpText(described)
    root.Add(listbox, 1, wx.EXPAND | wx.ALL, 8)

    buttons = wx.BoxSizer(wx.HORIZONTAL)
    snooze_btn = wx.Button(dialog, label="&Snooze...")
    snooze_btn.SetHelpText(
        "Pushes a reminder out by a few minutes, counted from now. Only "
        "reminders can be snoozed -- a recording has a start time to keep."
    )
    dismiss_btn = wx.Button(dialog, label="&Dismiss")
    dismiss_btn.SetHelpText(
        "Forgets the highlighted reminder. It does not cancel a recording: a "
        "recording is cancelled in Schedule Recording, where it was made."
    )
    open_btn = wx.Button(dialog, label="&Go There")
    open_btn.SetHelpText("Opens whatever the highlighted row is about.")
    close_btn = wx.Button(dialog, wx.ID_CLOSE, label="Cl&ose")
    close_btn.SetHelpText("Closes Upcoming. Nothing is changed.")
    for button in (snooze_btn, dismiss_btn, open_btn, close_btn):
        buttons.Add(button, 0, wx.RIGHT, 6)
    root.Add(buttons, 0, wx.ALL, 8)
    apply_modal_ids(dialog, affirmative_id=close_btn.GetId(), escape_id=close_btn.GetId())
    dialog.SetSizer(root)

    def _selected() -> tuple[str, Any] | None:
        index = listbox.GetSelection()
        if index == wx.NOT_FOUND or index >= len(rows):
            return None
        return rows[index]

    def _refresh(select: int = 0) -> None:
        now = datetime.now(UTC)
        rows[:] = _gather(host, data_dir, now)
        listbox.Set([label for label, _payload in rows])
        summary.SetLabel(_summarise(rows))
        if rows:
            listbox.SetSelection(max(0, min(select, len(rows) - 1)))
        _sync()

    def _sync() -> None:
        current = _selected()
        is_reminder = current is not None and isinstance(current[1], rem.Reminder)
        snooze_btn.Enable(is_reminder)
        dismiss_btn.Enable(is_reminder)
        open_btn.Enable(current is not None)
        if current is not None and not is_reminder:
            snooze_btn.SetHelpText("Not available: a scheduled recording has a start time to keep.")
            dismiss_btn.SetHelpText(
                "Not available: cancel a recording in Schedule Recording, where it was made."
            )

    def _on_snooze(_event: Any) -> None:
        current = _selected()
        if current is None or not isinstance(current[1], rem.Reminder):
            host._announce("Only a reminder can be snoozed.")
            return
        labels = [label for _seconds, label in SNOOZE_CHOICES]
        with wx.SingleChoiceDialog(dialog, "Snooze for:", "Snooze", labels) as chooser:
            if chooser.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            seconds, label = SNOOZE_CHOICES[max(0, chooser.GetSelection())]
        rem.snooze(data_dir, current[1].reminder_id, seconds)
        _refresh(listbox.GetSelection())
        host._announce(f"Snoozed {current[1].title} for {label}.")

    def _on_dismiss(_event: Any) -> None:
        current = _selected()
        if current is None or not isinstance(current[1], rem.Reminder):
            host._announce("Only a reminder can be dismissed here.")
            return
        index = listbox.GetSelection()
        rem.remove_reminder(data_dir, current[1].reminder_id)
        _refresh(index)
        host._announce(f"Dismissed the reminder for {current[1].title}.")

    def _on_open(_event: Any) -> None:
        current = _selected()
        if current is None:
            host._announce("Nothing is selected.")
            return
        host._announce(open_target(host, current[1]))
        dialog.EndModal(wx.ID_CLOSE)

    snooze_btn.Bind(wx.EVT_BUTTON, _on_snooze)
    dismiss_btn.Bind(wx.EVT_BUTTON, _on_dismiss)
    open_btn.Bind(wx.EVT_BUTTON, _on_open)
    close_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CLOSE))
    listbox.Bind(wx.EVT_LISTBOX, lambda _e: _sync())
    apply_listbox_activation(listbox, _on_open)
    _refresh()
    wx.CallAfter(listbox.SetFocus)
    try:
        host._show_modal_dialog(dialog, TITLE)
    finally:
        dialog.Destroy()


def _gather(host: Any, data_dir: Any, now: datetime) -> list[tuple[str, Any]]:
    """Reminders and scheduled recordings, merged and sorted by when.

    Both kinds carry their source in the row text, because Dismiss means two
    very different things depending on which one is highlighted.
    """
    rows: list[tuple[datetime, str, Any]] = []
    for reminder in rem.load_reminders(data_dir):
        if reminder.is_done:
            continue
        rows.append((reminder.fires_at, f"Reminder: {rem.row_label(reminder, now)}", reminder))
    for entry in _recordings(host):
        when = _entry_moment(entry)
        if when is None:
            continue
        name = str(getattr(entry, "station_name", "") or getattr(entry, "name", "") or "Recording")
        rows.append((when, f"Recording: {name}, {rem.spoken_when(when)}", entry))
    rows.sort(key=lambda row: row[0])
    return [(label, payload) for _when, label, payload in rows]


def _recordings(host: Any) -> list[Any]:
    """The scheduled recordings, or none when this app has no scheduler.

    Read defensively: Upcoming is worth showing with only reminders in it, and
    a scheduler that cannot be read must not empty the window.
    """
    try:
        from quill.core.paths import app_data_dir
        from quill.core.radio.recording_schedule import load_schedule

        return [entry for entry in load_schedule(app_data_dir()) if getattr(entry, "enabled", True)]
    except Exception:  # noqa: BLE001 - a missing scheduler is not an error here
        return []


def _entry_moment(entry: Any) -> datetime | None:
    for name in ("next_run_at", "next_occurrence", "when", "starts_at"):
        value = getattr(entry, name, None)
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        if isinstance(value, str) and value.strip():
            try:
                moment = datetime.fromisoformat(value)
            except ValueError:
                continue
            return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)
    return None


def _summarise(rows: list[tuple[str, Any]]) -> str:
    if not rows:
        return "Nothing is scheduled or reminded."
    reminders_count = sum(1 for _label, payload in rows if isinstance(payload, rem.Reminder))
    recordings = len(rows) - reminders_count
    parts = []
    if reminders_count:
        parts.append(f"{reminders_count} reminder{'' if reminders_count == 1 else 's'}")
    if recordings:
        parts.append(f"{recordings} scheduled recording{'' if recordings == 1 else 's'}")
    return " and ".join(parts) + "."


def open_target(host: Any, payload: Any) -> str:
    """Go to whatever a row is about; what to say either way.

    Public because the reminder toast's Go There button uses it too (7.6):
    "where does this kind of reminder lead?" is one question, and a second
    copy would drift the first time a kind was added.
    """
    if not isinstance(payload, rem.Reminder):
        opener = getattr(host, "open_schedule_recording", None)
        if callable(opener):
            opener()
            return "Opened Schedule Recording."
        return "Scheduled recording is not available here."
    if payload.kind == rem.KIND_EVENT:
        opener = getattr(host, "open_acb_calendar", None)
        if callable(opener):
            opener()
            return f"Opened the schedule. {payload.title} is in it."
    if payload.kind == rem.KIND_STATION and payload.target:
        controller = getattr(host, "_radio_controller", None)
        if controller is not None:
            from quill.core.radio.models import RadioStation

            controller.play_station(RadioStation(name=payload.title, stream_url=payload.target))
            return f"Playing {payload.title}."
    return f"{payload.title}: there is nowhere to go from here."


__all__ = ["SNOOZE_CHOICES", "TITLE", "open_target", "show_upcoming"]
