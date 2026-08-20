"""Internet Radio > Schedule Recording... -- record a station later, only
while QUILL is running (Tools > Media > Internet Radio).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse
from zoneinfo import available_timezones

from quill.core.radio.recording_schedule import RecordingScheduleEntry, new_id, next_occurrence
from quill.core.radio.wake_timer import parse_time_of_day
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button

_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

#: The timezone dropdown: "(local time)" (an empty entry.timezone) followed by
#: every IANA zone, so a Pacific user can pin an Eastern show to Eastern time.
_LOCAL_TIME_LABEL = "(local time)"
_TIMEZONE_CHOICES = (_LOCAL_TIME_LABEL, *sorted(available_timezones()))


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
    zone = f" {entry.timezone}" if entry.timezone else ""
    state = "" if entry.enabled else " (disabled)"
    # Show the stream's host so two entries with the same name/time (notably a
    # duplicate, which keeps the original's URL) are distinguishable in the list
    # instead of looking identical (#1220).
    host = urlparse(entry.stream_url).netloc if entry.stream_url else ""
    source = f" [{host}]" if host else ""
    return f"{entry.station_name} -- {when}{zone}, {entry.duration_minutes} min{state}{source}"


def build_schedule_entry(
    *,
    name: str,
    url: str,
    recurrence_index: int,
    time_text: str,
    date_text: str,
    weekday_index: int,
    timezone_name: str,
    duration_minutes: int,
    editing_id: str | None = None,
    now: datetime | None = None,
) -> tuple[RecordingScheduleEntry | None, str | None]:
    """Validate form values and build an entry (wx-free, so it is unit-testable).

    Returns ``(entry, None)`` on success or ``(None, message)`` on the first
    validation failure. ``time_text`` accepts 12-hour (``7:30 PM``) or 24-hour
    (``19:30``) via :func:`parse_time_of_day`; ``timezone_name`` empty means
    local time. A naive-local one-time recording must be in the future; a zoned
    one-time is judged in its own zone at fire time, so the future guard is
    skipped for it. ``editing_id`` reuses that id (edit in place) instead of
    minting a new one.
    """
    name = name.strip()
    url = url.strip()
    if not name or not url:
        return None, "A station name and a stream URL are both required."
    if duration_minutes < 1:
        return None, "Set a recording length of at least one minute."
    recurrence = ("once", "daily", "weekly")[recurrence_index if recurrence_index >= 0 else 0]
    normalized_time = parse_time_of_day(time_text)
    if not normalized_time:
        return None, "Time must be like 7:30 PM or 19:30."
    hour, minute = (int(part) for part in normalized_time.split(":", 1))
    if recurrence == "once":
        try:
            run_at = datetime.fromisoformat(f"{date_text.strip()}T{hour:02d}:{minute:02d}:00")
        except ValueError:
            return None, "Date must be in YYYY-MM-DD format."
        if not timezone_name and run_at <= (now or datetime.now()):
            return None, "Choose a date and time in the future."
        run_at_text = run_at.isoformat()
    else:
        run_at_text = f"2026-01-01T{hour:02d}:{minute:02d}:00"
    entry = RecordingScheduleEntry(
        id=editing_id or new_id(),
        station_name=name,
        stream_url=url,
        recurrence=recurrence,  # type: ignore[arg-type]
        run_at=run_at_text,
        weekday=weekday_index if recurrence == "weekly" else -1,
        duration_minutes=duration_minutes,
        timezone=timezone_name,
    )
    return entry, None


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
        on_update: Callable[[RecordingScheduleEntry], bool] | None = None,
        favorites: object | None = None,
        announce_cb: Callable[[str], None] | None = None,
        windows: object | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._menu_id_refs: list[object] = []
        self._entries = list(entries)
        self._on_add = on_add
        self._on_remove = on_remove
        self._on_update = on_update or (lambda _entry: False)
        self._favorites = favorites
        self._announce = announce_cb or (lambda _m: None)
        #: When set, the form is editing this existing entry in place (Save
        #: Changes) rather than adding a new one.
        self._editing_id: str | None = None

        # Modeless wx.Frame (menu bar + &Window menu, controls on an inner panel)
        # when standalone Radio supplies a WindowManager; modal wx.Dialog for
        # embedded QUILL.
        self._windows = windows
        self._modeless = windows is not None
        if self._modeless:
            self._win = wx.Frame(parent, title="Schedule Recording", style=wx.DEFAULT_FRAME_STYLE)
            self._surface = wx.Panel(self._win, style=wx.TAB_TRAVERSAL)
            self._build_surface_menu_bar()
            self._win.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
            self._win.Bind(wx.EVT_CLOSE, self._on_close)
        else:
            self._win = wx.Dialog(
                parent,
                title="Schedule Recording",
                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            )
            self._surface = self._win
        self.dialog = self._win  # back-compat alias for callers that reference it
        self._win.SetMinSize((560, 520))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(
            wx.StaticText(self._surface, label="&Scheduled recordings"), 0, wx.LEFT | wx.TOP, 10
        )
        # The requirement nobody discovers until a recording starts three
        # minutes late: a schedule is a thread inside a running app, so a
        # sleeping computer simply is not asked. Quill Radio now holds standby
        # off as the moment approaches and asks Windows to wake for it, and
        # both can be turned off -- so the honest thing is to say the
        # requirement out loud rather than imply it is handled.
        requirement = wx.StaticText(
            self._surface,
            label=(
                "Quill Radio must be running for a scheduled recording to start "
                "(the system tray counts). It keeps this computer awake as the "
                "time approaches, and can wake it if it is asleep."
            ),
        )
        requirement.Wrap(520)
        root.Add(requirement, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self._list = wx.ListBox(self._surface)
        self._list.SetName(
            "Scheduled recordings; Delete removes the selected one, Shift+F10 for actions"
        )
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 10)

        list_btns = wx.BoxSizer(wx.HORIZONTAL)
        self._edit_btn = wx.Button(self._surface, label="&Edit")
        self._edit_btn.SetName("Edit the selected schedule")
        self._edit_btn.Enable(False)
        self._duplicate_btn = wx.Button(self._surface, label="D&uplicate")
        self._duplicate_btn.SetName("Duplicate the selected schedule for a quick variation")
        self._duplicate_btn.Enable(False)
        self._toggle_btn = wx.Button(self._surface, label="Disab&le")
        self._toggle_btn.SetName("Enable or disable the selected schedule")
        self._toggle_btn.Enable(False)
        self._remove_btn = wx.Button(self._surface, label="&Remove")
        self._remove_btn.SetName("Remove the selected schedule")
        self._remove_btn.Enable(False)
        for btn in (self._edit_btn, self._duplicate_btn, self._toggle_btn, self._remove_btn):
            list_btns.Add(btn, 0, wx.RIGHT, 6)
        root.Add(list_btns, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        root.Add(wx.StaticLine(self._surface), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        root.Add(wx.StaticText(self._surface, label="Add a new schedule"), 0, wx.ALL, 10)

        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)

        # Pick a favorite instead of typing: choosing one fills the name and
        # URL below (both stay editable for one-off streams).
        favorite_entries = list(getattr(self._favorites, "favorites", []) or [])
        if favorite_entries:
            grid.Add(
                wx.StaticText(self._surface, label="&Favorite station:"),
                0,
                wx.ALIGN_CENTER_VERTICAL,
            )
            labels = ["(type the details below)"] + [f.display_label for f in favorite_entries]
            self._favorite_choice = wx.Choice(self._surface, choices=labels)
            self._favorite_choice.SetName(
                "Pick a favorite to record; it fills the station name and stream URL for you"
            )
            self._favorite_choice.SetSelection(0)
            self._favorite_entries = favorite_entries

            def _on_pick(_event: object) -> None:
                index = self._favorite_choice.GetSelection() - 1
                if 0 <= index < len(self._favorite_entries):
                    favorite = self._favorite_entries[index]
                    self._name_ctrl.SetValue(favorite.display_label)
                    self._url_ctrl.SetValue(favorite.station.stream_url)

            self._favorite_choice.Bind(wx.EVT_CHOICE, _on_pick)
            grid.Add(self._favorite_choice, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self._surface, label="Station &name:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._name_ctrl = wx.TextCtrl(self._surface, value=default_station_name)
        self._name_ctrl.SetName("Station name for this schedule")
        grid.Add(self._name_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self._surface, label="Stream &URL:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._url_ctrl = wx.TextCtrl(self._surface, value=default_stream_url)
        self._url_ctrl.SetName("Stream URL to record")
        grid.Add(self._url_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self._surface, label="&Repeats:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._recurrence_choice = wx.Choice(self._surface, choices=["Once", "Daily", "Weekly"])
        self._recurrence_choice.SetName("How often this recording repeats")
        self._recurrence_choice.SetSelection(0)
        grid.Add(self._recurrence_choice, 0)

        grid.Add(
            wx.StaticText(self._surface, label="On &day (weekly only):"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._weekday_choice = wx.Choice(self._surface, choices=list(_WEEKDAYS))
        self._weekday_choice.SetName("Day of the week, for a weekly schedule")
        self._weekday_choice.SetSelection(0)
        grid.Add(self._weekday_choice, 0)

        default_date = datetime.now() + timedelta(minutes=5)
        grid.Add(
            wx.StaticText(self._surface, label="&Date (once only):"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._date_ctrl = wx.TextCtrl(self._surface, value=default_date.strftime("%Y-%m-%d"))
        self._date_ctrl.SetName("Date for a one-time schedule, as YYYY-MM-DD")
        grid.Add(self._date_ctrl, 0)

        grid.Add(
            wx.StaticText(self._surface, label="&Time (7:30 PM or 19:30):"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._time_ctrl = wx.TextCtrl(self._surface, value=default_date.strftime("%H:%M"))
        self._time_ctrl.SetName("Time of day; accepts 12-hour like 7:30 PM or 24-hour like 19:30")
        grid.Add(self._time_ctrl, 0)

        grid.Add(wx.StaticText(self._surface, label="Time &zone:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._timezone_choice = wx.Choice(self._surface, choices=list(_TIMEZONE_CHOICES))
        self._timezone_choice.SetName(
            "Time zone for this recording; local time by default. Choose a zone to record a "
            "show in another region at its own local time"
        )
        self._timezone_choice.SetSelection(0)
        grid.Add(self._timezone_choice, 0)

        grid.Add(
            wx.StaticText(self._surface, label="Duration -- &hours:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._hours_ctrl = wx.SpinCtrl(self._surface, min=0, max=24)
        self._hours_ctrl.SetValue(1)
        self._hours_ctrl.SetName("Recording length, hours (0 to 24)")
        grid.Add(self._hours_ctrl, 0)

        grid.Add(wx.StaticText(self._surface, label="and &minutes:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._minutes_ctrl = wx.SpinCtrl(self._surface, min=0, max=59)
        self._minutes_ctrl.SetValue(0)
        self._minutes_ctrl.SetName("Recording length, minutes (0 to 59), added to the hours")
        grid.Add(self._minutes_ctrl, 0)

        root.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        self._status = wx.StaticText(self._surface, label="")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._add_btn = wx.Button(self._surface, label="&Add Schedule")
        self._new_btn = wx.Button(self._surface, label="Ne&w")
        self._new_btn.SetName("Clear the form and stop editing")
        self._new_btn.Enable(False)
        close_btn = wx.Button(self._surface, wx.ID_CANCEL, "Close")
        # A frame gets no free ID_CANCEL handling: wire it, or the
        # button that looks like the way out does nothing.
        bind_close_button(self._win, close_btn, modeless=self._modeless)
        btn_row.Add(self._add_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._new_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self._surface.SetSizer(root)
        if self._modeless:
            outer = wx.BoxSizer(wx.VERTICAL)
            outer.Add(self._surface, 1, wx.EXPAND)
            self._win.SetSizer(outer)

        self._remove_btn.Bind(wx.EVT_BUTTON, self._on_remove_click)
        self._edit_btn.Bind(wx.EVT_BUTTON, self._on_edit_click)
        self._duplicate_btn.Bind(wx.EVT_BUTTON, self._on_duplicate_click)
        self._toggle_btn.Bind(wx.EVT_BUTTON, self._on_toggle_click)
        self._add_btn.Bind(wx.EVT_BUTTON, self._on_add_click)
        self._new_btn.Bind(wx.EVT_BUTTON, lambda _e: self._reset_form())
        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._refresh_remove_button())
        self._list.Bind(wx.EVT_KEY_DOWN, self._on_list_key)
        self._list.Bind(wx.EVT_CONTEXT_MENU, self._on_list_context_menu)
        self._refresh_list()

    def _selected_entry(self) -> RecordingScheduleEntry | None:
        index = self._list.GetSelection()
        if 0 <= index < len(self._entries):
            return self._entries[index]
        return None

    def _refresh_remove_button(self) -> None:
        """Name each list action for its target and dim them when there is none."""
        entry = self._selected_entry()
        if entry is not None:
            name = entry.station_name
            self._remove_btn.SetLabel(f"&Remove {name}")
            self._remove_btn.SetName(f"Remove the {name} schedule")
            self._remove_btn.Enable(True)
            self._edit_btn.Enable(True)
            self._edit_btn.SetName(f"Edit the {name} schedule")
            self._duplicate_btn.Enable(True)
            self._duplicate_btn.SetName(f"Duplicate the {name} schedule")
            self._toggle_btn.Enable(True)
            if entry.enabled:
                self._toggle_btn.SetLabel("Disab&le")
                self._toggle_btn.SetName(f"Disable the {name} schedule")
            else:
                self._toggle_btn.SetLabel("Enab&le")
                self._toggle_btn.SetName(f"Enable the {name} schedule")
        else:
            self._remove_btn.SetLabel("&Remove")
            self._remove_btn.SetName("Remove the selected schedule")
            self._remove_btn.Enable(False)
            self._edit_btn.Enable(False)
            self._duplicate_btn.Enable(False)
            self._toggle_btn.Enable(False)
            self._toggle_btn.SetLabel("Disab&le")

    def _on_list_key(self, event: object) -> None:
        wx = self._wx
        if event.GetKeyCode() in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self._on_remove_click(None)
            return
        event.Skip()

    def _on_list_context_menu(self, _event: object) -> None:
        wx = self._wx
        index = self._list.GetSelection()
        if not (0 <= index < len(self._entries)):
            return
        entry = self._entries[index]
        menu = wx.Menu()
        edit_id = wx.NewIdRef()
        duplicate_id = wx.NewIdRef()
        toggle_id = wx.NewIdRef()
        delete_id = wx.NewIdRef()
        menu.Append(edit_id, "&Edit")
        menu.Append(duplicate_id, "D&uplicate")
        menu.Append(toggle_id, "Enab&le" if not entry.enabled else "Disab&le")
        menu.Append(delete_id, f"&Delete {entry.station_name}\tDelete")
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_edit_click(None), id=edit_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_duplicate_click(None), id=duplicate_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_toggle_click(None), id=toggle_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_remove_click(None), id=delete_id)
        # pinned while the popup can fire
        self._context_menu_id_refs = [edit_id, duplicate_id, toggle_id, delete_id]
        self._list.PopupMenu(menu)
        menu.Destroy()

    def _build_surface_menu_bar(self) -> None:
        wx = self._wx
        menu_bar = wx.MenuBar()
        surface_menu = wx.Menu()
        close_id = wx.NewIdRef()
        surface_menu.Append(close_id, "&Close\tCtrl+W")
        self._win.Bind(wx.EVT_MENU, lambda _e: self._win.Close(), id=close_id)
        menu_bar.Append(surface_menu, "&Schedule")
        self._windows.install(self._win, menu_bar)
        self._win.SetMenuBar(menu_bar)
        self._menu_id_refs.append(close_id)

    def _on_char_hook(self, event: object) -> None:
        if event.GetKeyCode() == self._wx.WXK_ESCAPE:
            self._win.Close()
            return
        event.Skip()

    def _on_close(self, event: object) -> None:
        previous = self._windows.previous_key(self._win)
        self._windows.unregister(self._win)
        self._announce("Exited Schedule Recording.")
        event.Skip()
        self._win.Destroy()
        if previous:
            self._windows.activate(previous)

    def show(self) -> None:
        if self._modeless:
            from quill.ui.dialog_contract import show_modeless_surface

            self._windows.register(self._win, "Schedule Recording")
            show_modeless_surface(self._win, "Schedule Recording", announce=self._announce)
            return
        self._win.CentreOnParent()
        apply_modal_ids(self._win, cancel_id=self._wx.ID_CANCEL)
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self._win, "Schedule Recording", announce=self._announce)
        finally:
            self._win.Destroy()

    def _refresh_list(self, keep_id: str | None = None) -> None:
        # Order the list the way the recordings actually occur, not the order
        # they were entered (#1220). Sorting self._entries in place keeps the
        # index-based selection (_selected_entry / keep_id) in step with the
        # display. Undetermined times sort last, then by name for stability.
        far_future = datetime.max.replace(tzinfo=UTC)
        now = datetime.now()
        self._entries.sort(
            key=lambda e: (next_occurrence(e, now) or far_future, e.station_name.lower())
        )
        self._list.Clear()
        for entry in self._entries:
            self._list.Append(_entry_summary(entry), entry.id)
        selected = 0
        if keep_id is not None:
            for index, entry in enumerate(self._entries):
                if entry.id == keep_id:
                    selected = index
                    break
        if self._entries:
            self._list.SetSelection(selected)
        self._refresh_remove_button()

    def _on_remove_click(self, _event: object) -> None:
        index = self._list.GetSelection()
        if index == self._wx.NOT_FOUND:
            return
        entry_id = self._list.GetClientData(index)
        if self._on_remove(entry_id):
            self._entries = [e for e in self._entries if e.id != entry_id]
            if self._editing_id == entry_id:
                self._reset_form()
            self._refresh_list()
            self._announce("Removed scheduled recording.")

    def _enter_add_mode(self) -> None:
        """Leave edit mode: the primary button adds a new schedule again."""
        self._editing_id = None
        self._add_btn.SetLabel("&Add Schedule")
        self._new_btn.Enable(False)

    def _reset_form(self) -> None:
        """Clear the inputs and return to add mode (the New button)."""
        self._name_ctrl.SetValue("")
        self._url_ctrl.SetValue("")
        self._recurrence_choice.SetSelection(0)
        self._weekday_choice.SetSelection(0)
        self._timezone_choice.SetSelection(0)
        # Reset Date/Time to the same now+5min default the form opened with, so a
        # previously-edited entry's values don't linger into the next add.
        default_moment = datetime.now() + timedelta(minutes=5)
        self._date_ctrl.SetValue(default_moment.strftime("%Y-%m-%d"))
        self._time_ctrl.SetValue(default_moment.strftime("%H:%M"))
        self._hours_ctrl.SetValue(1)
        self._minutes_ctrl.SetValue(0)
        self._status.SetLabel("")
        self._enter_add_mode()

    def _load_entry_into_form(self, entry: RecordingScheduleEntry) -> None:
        """Populate the form fields from an existing entry (edit/duplicate)."""
        self._name_ctrl.SetValue(entry.station_name)
        self._url_ctrl.SetValue(entry.stream_url)
        self._recurrence_choice.SetSelection(("once", "daily", "weekly").index(entry.recurrence))
        if 0 <= entry.weekday < 7:
            self._weekday_choice.SetSelection(entry.weekday)
        try:
            moment = datetime.fromisoformat(entry.run_at)
            self._time_ctrl.SetValue(moment.strftime("%H:%M"))
            if entry.recurrence == "once":
                self._date_ctrl.SetValue(moment.strftime("%Y-%m-%d"))
        except ValueError:
            pass
        self._hours_ctrl.SetValue(entry.duration_minutes // 60)
        self._minutes_ctrl.SetValue(entry.duration_minutes % 60)
        if entry.timezone and entry.timezone in _TIMEZONE_CHOICES:
            self._timezone_choice.SetSelection(_TIMEZONE_CHOICES.index(entry.timezone))
        else:
            self._timezone_choice.SetSelection(0)

    def _on_edit_click(self, _event: object) -> None:
        entry = self._selected_entry()
        if entry is None:
            return
        self._load_entry_into_form(entry)
        self._editing_id = entry.id
        self._add_btn.SetLabel("&Save Changes")
        self._new_btn.Enable(True)
        self._status.SetLabel(
            f"Editing {entry.station_name}. Change the fields, then choose Save Changes."
        )
        self._name_ctrl.SetFocus()

    def _on_duplicate_click(self, _event: object) -> None:
        entry = self._selected_entry()
        if entry is None:
            return
        self._load_entry_into_form(entry)
        self._enter_add_mode()  # a duplicate is a new entry, not an edit
        self._name_ctrl.SetValue(f"{entry.station_name} (copy)")
        self._status.SetLabel("Duplicated. Adjust the fields, then choose Add Schedule.")
        self._name_ctrl.SetFocus()

    def _on_toggle_click(self, _event: object) -> None:
        entry = self._selected_entry()
        if entry is None:
            return
        updated = replace(entry, enabled=not entry.enabled)
        if self._on_update(updated):
            self._entries = [updated if e.id == updated.id else e for e in self._entries]
            self._refresh_list(keep_id=updated.id)
            state = "enabled" if updated.enabled else "disabled"
            self._announce(f"{updated.station_name} {state}.")

    def _build_entry_from_form(self) -> RecordingScheduleEntry | None:
        """Read the controls, validate via the pure builder, show any error."""
        tz_index = self._timezone_choice.GetSelection()
        entry, error = build_schedule_entry(
            name=self._name_ctrl.GetValue(),
            url=self._url_ctrl.GetValue(),
            recurrence_index=self._recurrence_choice.GetSelection(),
            time_text=self._time_ctrl.GetValue(),
            date_text=self._date_ctrl.GetValue(),
            weekday_index=self._weekday_choice.GetSelection(),
            timezone_name="" if tz_index <= 0 else _TIMEZONE_CHOICES[tz_index],
            duration_minutes=self._hours_ctrl.GetValue() * 60 + self._minutes_ctrl.GetValue(),
            editing_id=self._editing_id,
        )
        if error:
            self._status.SetLabel(error)
            return None
        return entry

    def _on_add_click(self, _event: object) -> None:
        entry = self._build_entry_from_form()
        if entry is None:
            return
        if self._editing_id:
            if self._on_update(entry):
                self._entries = [entry if e.id == entry.id else e for e in self._entries]
                self._enter_add_mode()
                self._refresh_list(keep_id=entry.id)
                self._reset_form()
                self._status.SetLabel(f"Saved: {_entry_summary(entry)}")
                self._announce(f"Saved changes to {entry.station_name}.")
                self._focus_saved_entry()
            return
        self._on_add(entry)
        self._entries.append(entry)
        self._refresh_list(keep_id=entry.id)
        self._reset_form()
        self._status.SetLabel(f"Added: {_entry_summary(entry)}")
        self._announce(f"Scheduled recording added for {entry.station_name}.")
        self._focus_saved_entry()

    def _focus_saved_entry(self) -> None:
        """After Add/Save, land on the entry in the list -- not back on the Add
        button, which read as "press me again to add another" (#1220)."""
        if self._entries:
            self._list.SetFocus()
