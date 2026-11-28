"""Weather on a Past Date: type a date, read the day, move a day, a week, a
month or a year at a time.

Thin wx over ``quill.core.weather.date_query`` (what was typed),
``past_day_service`` (the day, on a worker thread) and ``past_day_text`` (the
words). Built for the ear:

* The date is a plain text field, not a calendar control, because a date
  picker reads poorly with a screen reader. Whatever is typed stays in the
  field when it cannot be used, and the reason is said.
* Every move says the new date first and then the day in brief; the whole day
  is in the read-only "Weather that day" box, and each hour is a list row.
* A year or a month and year opens that span as a list of days; Enter on a
  day opens it.
* The last ten dates looked at are a list; Enter on one opens it again.

Keys (also in the guide and the F1 help), chosen with the Desktop
Accessibility Specialist: Alt+Left and Alt+Right a day, with Shift a week;
Page Up and Page Down a day, with Shift a week, except in the reading box, the
lists and the Place dropdown, where they keep their own meaning; Ctrl+Page Up
and Ctrl+Page Down a month; Ctrl+Shift+Page Up and Ctrl+Shift+Page Down a year
(the same day last or next year); Ctrl+G, the Date field; Ctrl+S, Save Range.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from quill.core.weather import date_query, past_day_text, recent_dates
from quill.ui.dialog_contract import (
    apply_modal_ids,
    bind_close_button,
    set_accessible_name,
    show_modal_dialog,
)
from quill.ui.dpi import dip, dip_size
from quill.ui.surface_lifetime import surface_tasks
from quill.ui.weather.past_date_lists import PastDateListsMixin, short_note

_HOUR_COLUMNS = (
    ("Time", 80),
    ("Conditions", 140),
    ("Temperature", 90),
    ("Feels like", 80),
    ("Precipitation", 110),
    ("Wind", 200),
)
_SPAN_COLUMNS = (
    ("Date", 150),
    ("Conditions", 140),
    ("High", 60),
    ("Low", 60),
    ("Precipitation", 140),
)

#: (key code name, shift, ctrl, alt) -> (days, months, years). Page keys are
#: left alone in lists, where they move through the rows.
MOVES: dict[tuple[str, bool, bool, bool], tuple[int, int, int]] = {
    ("LEFT", False, False, True): (-1, 0, 0),
    ("RIGHT", False, False, True): (1, 0, 0),
    ("PAGEUP", False, False, False): (-1, 0, 0),
    ("PAGEDOWN", False, False, False): (1, 0, 0),
    ("LEFT", True, False, True): (-7, 0, 0),
    ("RIGHT", True, False, True): (7, 0, 0),
    ("PAGEUP", True, False, False): (-7, 0, 0),
    ("PAGEDOWN", True, False, False): (7, 0, 0),
    ("PAGEUP", False, True, False): (0, -1, 0),
    ("PAGEDOWN", False, True, False): (0, 1, 0),
    ("PAGEUP", True, True, False): (0, 0, -1),
    ("PAGEDOWN", True, True, False): (0, 0, 1),
}


class PastDateDialog(PastDateListsMixin):
    def __init__(
        self,
        parent: object,
        *,
        data_dir: Path,
        task_manager: object,
        safe_mode: bool,
        announce_cb: Callable[[str], None] | None = None,
        health: Any = None,
        on_health_changed: Callable[[], None] | None = None,
        place_id: str = "",
        start: date | None = None,
        today: date | None = None,
        date_order: str | None = None,
    ) -> None:
        import wx

        from quill.core.weather import locations as loc_store
        from quill.core.weather import settings as settings_mod

        self._wx = wx
        self._data_dir = data_dir
        self._safe_mode = safe_mode
        self._announce = announce_cb or (lambda _m: None)
        self._health = health
        self._on_health_changed = on_health_changed or (lambda: None)
        self._today = today or date.today()
        self._order = date_order or date_query.system_date_order()
        self._store = loc_store.load_locations(data_dir)
        settings = settings_mod.load_settings(data_dir)
        self._units = past_day_text.Units(settings.temperature_unit, settings.wind_unit)
        self._recent = recent_dates.load(data_dir)
        self._request = 0
        self.current: date | None = None
        self._day_text = ""
        self._credits = ""
        self._day: Any = None
        self._span_rows: list[Any] = []
        self._hour_row = 0
        self._start: date | None = None
        self.dialog = wx.Dialog(
            parent,
            title="Weather on a Past Date",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._task_manager = surface_tasks(task_manager, lambda: getattr(self, "dialog", None))
        dlg = self.dialog
        gap = dip(dlg, 12)
        root = wx.BoxSizer(wx.VERTICAL)

        top = wx.FlexGridSizer(cols=3, vgap=dip(dlg, 6), hgap=dip(dlg, 8))
        top.AddGrowableCol(1)
        top.Add(wx.StaticText(dlg, label="&Place:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._place = wx.Choice(dlg, choices=[loc.label for loc in self._store.locations])
        self._place.SetHelpText(
            "The saved place to show. Changing it shows the same date for the new place."
        )
        top.Add(self._place, 1, wx.EXPAND)
        top.AddSpacer(0)
        top.Add(wx.StaticText(dlg, label="&Date:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._date = wx.TextCtrl(dlg, style=wx.TE_PROCESS_ENTER)
        self._date.SetHelpText(
            "Type a date and press Enter: 2011-03-14, March 14, 2011, 14 March 2011, "
            "3/14/2011, yesterday, 3 days ago, last week, or a year ago today. A year "
            "alone, or a month and year, lists every day in it. Ctrl+G comes back here."
        )
        top.Add(self._date, 1, wx.EXPAND)
        self._go = wx.Button(dlg, wx.ID_ANY, "&Go")
        self._go.SetHelpText("Show the date typed in the Date field. Enter does the same.")
        top.Add(self._go)
        root.Add(top, 0, wx.EXPAND | wx.ALL, gap)

        self._status = wx.StaticText(dlg, label="")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, gap)

        root.Add(wx.StaticText(dlg, label="&Weather that day:"), 0, wx.ALL, gap)
        self._view = wx.TextCtrl(
            dlg,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            size=dip_size(dlg, 620, 150),
        )
        set_accessible_name(self._view, "Weather that day")
        self._view.SetHelpText(
            "The day read like the current report: the sky, high and low, feels like, "
            "rain and snow, wind, sunrise and sunset, and how it compared with normal. "
            "Alt+Left and Alt+Right move a day; add Shift for a week. Here Page Up "
            "and Page Down page through the text, as they always do."
        )
        root.Add(self._view, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, gap)

        root.Add(wx.StaticText(dlg, label="&Hour by hour:"), 0, wx.ALL, gap)
        self._hours = wx.ListCtrl(
            dlg, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=dip_size(dlg, 620, 150)
        )
        for i, (title, width) in enumerate(_HOUR_COLUMNS):
            self._hours.InsertColumn(i, title, width=dip(dlg, width))
        set_accessible_name(self._hours, "Hour by hour")
        self._hours.SetHelpText(
            "Each hour of the day: the time, the sky, the temperature, what it felt "
            "like, precipitation and wind."
        )
        root.Add(self._hours, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, gap)

        self._span_label = wx.StaticText(dlg, label="Day&s in this span:")
        root.Add(self._span_label, 0, wx.ALL, gap)
        self._span = wx.ListCtrl(
            dlg, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=dip_size(dlg, 620, 150)
        )
        for i, (title, width) in enumerate(_SPAN_COLUMNS):
            self._span.InsertColumn(i, title, width=dip(dlg, width))
        set_accessible_name(self._span, "Days in this span")
        self._span.SetHelpText(
            "Every day in the year or month you typed, oldest first. Press Enter on a "
            "day to open it."
        )
        root.Add(self._span, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, gap)

        root.Add(wx.StaticText(dlg, label="&Recent dates:"), 0, wx.ALL, gap)
        self._recent_list = wx.ListBox(dlg, size=dip_size(dlg, 620, 90))
        set_accessible_name(self._recent_list, "Recent dates")
        self._recent_list.SetHelpText(
            "The last ten dates you looked at, newest first, with their places. Press "
            "Enter on one to open it again."
        )
        root.Add(self._recent_list, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, gap)

        moves = wx.BoxSizer(wx.HORIZONTAL)
        self._back = wx.Button(dlg, wx.ID_ANY, "&Back a Day")
        self._back.SetHelpText(
            "Show the day before. Alt+Left does the same anywhere, and Page Up outside "
            "the text box, the lists and the Place dropdown."
        )
        self._fwd = wx.Button(dlg, wx.ID_ANY, "&Forward a Day")
        self._fwd.SetHelpText(
            "Show the day after. Alt+Right does the same anywhere, and Page Down outside "
            "the text box, the lists and the Place dropdown."
        )
        self._last_year = wx.Button(dlg, wx.ID_ANY, "Same Day &Last Year")
        self._last_year.SetHelpText(
            "Show this date a year earlier. Ctrl+Shift+Page Up does the same."
        )
        self._next_year = wx.Button(dlg, wx.ID_ANY, "Same Day Ne&xt Year")
        self._next_year.SetHelpText(
            "Show this date a year later. Ctrl+Shift+Page Down does the same."
        )
        for button in (self._back, self._fwd, self._last_year, self._next_year):
            moves.Add(button, 0, wx.RIGHT, dip(dlg, 6))
        root.Add(moves, 0, wx.LEFT | wx.RIGHT | wx.TOP, gap)

        bottom = wx.BoxSizer(wx.HORIZONTAL)
        self._copy = wx.Button(dlg, wx.ID_ANY, "&Copy Day")
        self._copy.SetHelpText("Copy the day, every hour and the data credits as text.")
        self._save = wx.Button(dlg, wx.ID_ANY, "Sa&ve Range...")
        self._save.SetHelpText(
            "Save every day between two dates as a spreadsheet file (CSV) or as text. "
            "Ctrl+S does the same."
        )
        bottom.Add(self._copy, 0, wx.RIGHT, dip(dlg, 6))
        bottom.Add(self._save)
        bottom.AddStretchSpacer()
        close_btn = wx.Button(dlg, wx.ID_CANCEL, "Close")
        close_btn.SetHelpText("Close this window. Escape does the same.")
        bottom.Add(close_btn)
        root.Add(bottom, 0, wx.EXPAND | wx.ALL, gap)

        self._credits_label = wx.StaticText(dlg, label="")
        root.Add(self._credits_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, gap)

        dlg.SetSizer(root)
        dlg.SetMinSize(dip_size(dlg, 680, 640))
        self._show_span(False)
        root.Fit(dlg)

        self._date.Bind(wx.EVT_TEXT_ENTER, lambda _e: self.go())
        self._go.Bind(wx.EVT_BUTTON, lambda _e: self.go())
        self._back.Bind(wx.EVT_BUTTON, lambda _e: self.move(-1, 0, 0))
        self._fwd.Bind(wx.EVT_BUTTON, lambda _e: self.move(1, 0, 0))
        self._last_year.Bind(wx.EVT_BUTTON, lambda _e: self.move(0, 0, -1))
        self._next_year.Bind(wx.EVT_BUTTON, lambda _e: self.move(0, 0, 1))
        self._copy.Bind(wx.EVT_BUTTON, lambda _e: self.copy())
        self._save.Bind(wx.EVT_BUTTON, lambda _e: self.save_range())
        self._place.Bind(wx.EVT_CHOICE, lambda _e: self._place_changed())
        self._span.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda e: self._open_span_row(e.GetIndex()))
        self._recent_list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self._open_recent())
        dlg.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        bind_close_button(dlg, close_btn, modeless=False)

        self._select_place(place_id)
        self._fill_recent()
        self._sync_buttons()
        if not self._store.locations:
            self._go.Disable()
            self._status.SetLabel("No saved places yet. Add one with Weather, Add Location.")
        elif start is not None:
            self._date.SetValue(start.isoformat())
        self._start = start

    # -- places --------------------------------------------------------------------

    def _select_place(self, place_id: str) -> None:
        locations = self._store.locations
        index = next((i for i, loc in enumerate(locations) if loc.id == place_id), -1)
        if index < 0:
            primary = self._store.primary()
            index = locations.index(primary) if primary in locations else 0
        if locations:
            self._place.SetSelection(index)

    def _location(self) -> Any:
        index = self._place.GetSelection()
        locations = self._store.locations
        return locations[index] if 0 <= index < len(locations) else None

    def _place_changed(self) -> None:
        if self.current is not None:
            self.show_day(self.current, announce_move="")

    # -- keys ----------------------------------------------------------------------

    def _on_char_hook(self, event: Any) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        ctrl, shift, alt = event.ControlDown(), event.ShiftDown(), event.AltDown()
        focus = wx.Window.FindFocus()
        if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and focus is self._recent_list:
            self._open_recent()
            return
        if ctrl and not alt and code in (ord("G"), ord("g")):
            self._date.SetFocus()
            self._date.SelectAll()
            return
        if ctrl and not alt and not shift and code in (ord("S"), ord("s")):
            self.save_range()
            return
        names = {
            wx.WXK_LEFT: "LEFT",
            wx.WXK_RIGHT: "RIGHT",
            wx.WXK_PAGEUP: "PAGEUP",
            wx.WXK_PAGEDOWN: "PAGEDOWN",
        }
        name = names.get(code)
        step = MOVES.get((name, shift, ctrl, alt)) if name else None
        # Page Up and Page Down keep their own meaning where they have one: in the
        # lists, the Place dropdown and the reading box (where they page the caret
        # and, with Shift, select). Alt+arrows and the Ctrl+Page keys work anywhere.
        page_owner = focus is self._view or isinstance(focus, wx.ListCtrl | wx.ListBox | wx.Choice)
        if step is None or (name in ("PAGEUP", "PAGEDOWN") and page_owner and not ctrl):
            event.Skip()
            return
        self.move(*step)

    # -- going to a date -----------------------------------------------------------

    def go(self) -> None:
        """Understand the Date field and show the day, or the span to browse."""
        text = self._date.GetValue()
        try:
            query = date_query.parse(text, today=self._today, order=self._order)
        except date_query.DateNotUnderstood as exc:
            self._say(str(exc.args[0]))  # the field keeps what was typed
            return
        if query.is_span:
            clipped, why = date_query.clip_span(query, today=self._today)
            if clipped is None:
                self._say(why)
                return
            self.show_span(clipped.start, clipped.end)
            return
        ok, why = date_query.check(query.start, today=self._today)
        if not ok:
            self._say(why)
            return
        note = " ".join(part for part in (query.note, why) if part)
        self.show_day(query.start, announce_move="", note=note)

    def move(self, days: int, months: int, years: int) -> None:
        if self.current is None:
            self._say("Go to a date first. Type one in the Date field and press Enter.")
            return
        target = date_query.shift(self.current, days=days, months=months, years=years)
        ok, why = date_query.check(target, today=self._today)
        if not ok:
            self._say(why)
            return
        self.show_day(target, announce_move="move", note=why)

    def show_day(self, day: date, *, announce_move: str, note: str = "") -> None:
        """Fetch and show *day* on a worker thread; the newest request wins."""
        from quill.core.weather import past_day_service

        location = self._location()
        if location is None:
            self._say("No saved places yet. Add one with Weather, Add Location.")
            return
        self.current = day
        self._date.ChangeValue(day.isoformat())
        self._sync_buttons()
        self._request = request = self._request + 1
        self._status.SetLabel(f"Getting {date_query.long_date(day)}...")
        units, data_dir, health = self._units, self._data_dir, self._health
        today = self._today

        def _work(**_kwargs: Any) -> object:
            return past_day_service.look_up_day(
                day,
                place=location.label,
                latitude=location.latitude,
                longitude=location.longitude,
                units=units,
                data_dir=data_dir,
                today=today,
                health=health,
            )

        def landed(result: object) -> None:
            self._day_landed(request, day, location, result, announce_move, note)

        if self._task_manager is None:
            landed(_work())
            return
        self._task_manager.submit(
            "weather-past-day",
            _work,
            on_success=lambda _op, result: landed(result),
            on_failure=lambda _op, exc: landed(exc),
        )

    def _day_landed(
        self,
        request: int,
        day: date,
        location: Any,
        result: object,
        announce_move: str,
        note: str,
    ) -> None:
        from quill.core.weather.past_day_service import DayResult

        if request != self._request:
            return  # a newer move owns the window
        self._on_health_changed()
        when = date_query.long_date(day)
        if not isinstance(result, DayResult):
            self._show_text(f"Could not get {when}. {result}")
            self._fill_hours([])
            self._say(f"{when}. Could not get this day. {result}")
            return
        self._day = result.day
        self._credits = result.credits
        self._show_text(result.text)
        self._fill_hours(result.day.hours if result.day else [])
        self._credits_label.SetLabel(result.credits)
        self._credits_label.Wrap(dip(self.dialog, 640))
        self._status.SetLabel(note or when)
        if result.day is not None:
            self._remember(day, location)
        self.dialog.Layout()
        spoken = " ".join(part for part in (f"{when}.", short_note(note), result.spoken) if part)
        if self._hours.HasFocus() and self._hours.GetItemCount():
            # The list just refilled under focus: put focus back on a row so the
            # reader has somewhere to be, then speak once it has settled.
            row = min(self._hour_row, self._hours.GetItemCount() - 1)
            self._hours.Select(row)
            self._hours.Focus(row)
            self._wx.CallAfter(self._announce, spoken)
            return
        self._announce(spoken)

    def _show_text(self, text: str) -> None:
        self._day_text = text
        self._view.SetValue(text)
        self._view.SetInsertionPoint(0)

    def _fill_hours(self, hours: list[Any]) -> None:
        self._hour_row = max(0, self._hours.GetFirstSelected())
        self._hours.DeleteAllItems()
        for i, hour in enumerate(hours):
            cells = past_day_text.hour_cells(hour, self._units)
            index = self._hours.InsertItem(i, cells[0])
            for col, value in enumerate(cells[1:], start=1):
                self._hours.SetItem(index, col, value)

    # -- speech --------------------------------------------------------------------

    def _say(self, text: str) -> None:
        self._status.SetLabel(text)
        self._announce(text)

    def show(self) -> None:
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_CANCEL,
            affirmative_label="Close",
            cancel_id=self._wx.ID_CANCEL,
            cancel_label="Close",
        )
        self._wx.CallAfter(self._date.SetFocus)
        if self._start is not None and self._store.locations:
            self._wx.CallAfter(self.show_day, self._start, announce_move="")
        try:
            show_modal_dialog(self.dialog, "Weather on a Past Date", announce=self._announce)
        finally:
            self.dialog.Destroy()
