"""Internet Radio > Schedule Recording... -- record a station later, only
while QUILL is running (Tools > Media > Internet Radio).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from quill.core.radio.recording_schedule import RecordingScheduleEntry, new_id
from quill.ui.dialog_contract import apply_modal_ids

_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def _entry_summary(entry: RecordingScheduleEntry) -> str:
    try:
        moment = datetime.fromisoformat(entry.run_at)
        time_text = moment.strftime("%H:%M")
    except ValueError:
        time_text = entry.run_at
    if entry.recurrence == "once":
        when = f"once at {entry.run_at.replace('T', ' ')}"
    elif entry.recurrence == "daily":
        when = f"daily at {time_text}"
    else:
        weekday = _WEEKDAYS[entry.weekday] if 0 <= entry.weekday < 7 else "?"
        when = f"every {weekday} at {time_text}"
    state = "" if entry.enabled else " (disabled)"
    return f"{entry.station_name} -- {when}, {entry.duration_minutes} min{state}"


class ScheduleRecordingDialog:
    """Add, remove, and review scheduled radio recordings."""

    def __init__(
        self,
        parent: object,
        *,
        entries: list[RecordingScheduleEntry],
        default_station_name: str = "",
        default_stream_url: str = "",
        on_add: Callable[[RecordingScheduleEntry], None],
        on_remove: Callable[[str], bool],
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._entries = list(entries)
        self._on_add = on_add
        self._on_remove = on_remove
        self._announce = announce_cb or (lambda _m: None)

        self.dialog = wx.Dialog(
            parent, title="Schedule Recording", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((560, 520))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(self.dialog, label="&Scheduled recordings"), 0, wx.LEFT | wx.TOP, 10)
        self._list = wx.ListBox(self.dialog)
        self._list.SetName("Scheduled recordings; select one and press Remove to delete it")
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 10)

        remove_btn = wx.Button(self.dialog, label="&Remove Selected")
        root.Add(remove_btn, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        root.Add(wx.StaticLine(self.dialog), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        root.Add(wx.StaticText(self.dialog, label="Add a new schedule"), 0, wx.ALL, 10)

        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)

        grid.Add(wx.StaticText(self.dialog, label="Station &name:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._name_ctrl = wx.TextCtrl(self.dialog, value=default_station_name)
        self._name_ctrl.SetName("Station name for this schedule")
        grid.Add(self._name_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self.dialog, label="Stream &URL:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._url_ctrl = wx.TextCtrl(self.dialog, value=default_stream_url)
        self._url_ctrl.SetName("Stream URL to record")
        grid.Add(self._url_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self.dialog, label="&Repeats:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._recurrence_choice = wx.Choice(self.dialog, choices=["Once", "Daily", "Weekly"])
        self._recurrence_choice.SetName("How often this recording repeats")
        self._recurrence_choice.SetSelection(0)
        grid.Add(self._recurrence_choice, 0)

        grid.Add(
            wx.StaticText(self.dialog, label="On &day (weekly only):"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._weekday_choice = wx.Choice(self.dialog, choices=list(_WEEKDAYS))
        self._weekday_choice.SetName("Day of the week, for a weekly schedule")
        self._weekday_choice.SetSelection(0)
        grid.Add(self._weekday_choice, 0)

        default_date = datetime.now() + timedelta(minutes=5)
        grid.Add(
            wx.StaticText(self.dialog, label="&Date (once only):"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._date_ctrl = wx.TextCtrl(self.dialog, value=default_date.strftime("%Y-%m-%d"))
        self._date_ctrl.SetName("Date for a one-time schedule, as YYYY-MM-DD")
        grid.Add(self._date_ctrl, 0)

        grid.Add(
            wx.StaticText(self.dialog, label="&Time (24-hour HH:MM):"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._time_ctrl = wx.TextCtrl(self.dialog, value=default_date.strftime("%H:%M"))
        self._time_ctrl.SetName("Time of day, as HH:MM in 24-hour time")
        grid.Add(self._time_ctrl, 0)

        grid.Add(
            wx.StaticText(self.dialog, label="&Duration (minutes):"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._duration_ctrl = wx.SpinCtrl(self.dialog, min=1, max=1440)
        self._duration_ctrl.SetValue(60)
        self._duration_ctrl.SetName("How many minutes to record")
        grid.Add(self._duration_ctrl, 0)

        root.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        add_btn = wx.Button(self.dialog, label="&Add Schedule")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        btn_row.Add(add_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        remove_btn.Bind(wx.EVT_BUTTON, self._on_remove_click)
        add_btn.Bind(wx.EVT_BUTTON, self._on_add_click)
        self._refresh_list()

    def show(self) -> None:
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, cancel_id=self._wx.ID_CANCEL)
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self.dialog, "Schedule Recording", announce=self._announce)
        finally:
            self.dialog.Destroy()

    def _refresh_list(self) -> None:
        self._list.Clear()
        for entry in self._entries:
            self._list.Append(_entry_summary(entry), entry.id)

    def _on_remove_click(self, _event: object) -> None:
        index = self._list.GetSelection()
        if index == self._wx.NOT_FOUND:
            return
        entry_id = self._list.GetClientData(index)
        if self._on_remove(entry_id):
            self._entries = [e for e in self._entries if e.id != entry_id]
            self._refresh_list()
            self._announce("Removed scheduled recording")

    def _on_add_click(self, _event: object) -> None:
        name = self._name_ctrl.GetValue().strip()
        url = self._url_ctrl.GetValue().strip()
        if not name or not url:
            self._status.SetLabel("A station name and a stream URL are both required.")
            return
        recurrence_index = self._recurrence_choice.GetSelection()
        recurrence = ("once", "daily", "weekly")[recurrence_index if recurrence_index >= 0 else 0]
        time_text = self._time_ctrl.GetValue().strip()
        try:
            hour, minute = (int(part) for part in time_text.split(":", 1))
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError
        except ValueError:
            self._status.SetLabel("Time must be in 24-hour HH:MM format, e.g. 08:00.")
            return
        weekday = self._weekday_choice.GetSelection()
        if recurrence == "once":
            date_text = self._date_ctrl.GetValue().strip()
            try:
                run_at = datetime.fromisoformat(f"{date_text}T{hour:02d}:{minute:02d}:00")
            except ValueError:
                self._status.SetLabel("Date must be in YYYY-MM-DD format.")
                return
            if run_at <= datetime.now():
                self._status.SetLabel("Choose a date and time in the future.")
                return
            run_at_text = run_at.isoformat()
        else:
            run_at_text = f"2026-01-01T{hour:02d}:{minute:02d}:00"

        entry = RecordingScheduleEntry(
            id=new_id(),
            station_name=name,
            stream_url=url,
            recurrence=recurrence,  # type: ignore[arg-type]
            run_at=run_at_text,
            weekday=weekday if recurrence == "weekly" else -1,
            duration_minutes=self._duration_ctrl.GetValue(),
        )
        self._on_add(entry)
        self._entries.append(entry)
        self._refresh_list()
        self._status.SetLabel(f"Added: {_entry_summary(entry)}")
        self._announce(f"Scheduled recording added for {name}")
