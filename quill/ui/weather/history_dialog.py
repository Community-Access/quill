"""Weather History: on this day, the same date over many years, or a date range.

Thin wx over ``quill.core.weather.history_service``, which does the fetching,
caching and wording on a worker thread. The window is built for the ear:

* The summary is a multi-line read-only text box, so the review cursor reads it
  sentence by sentence, and it is spoken once when a lookup lands (a background
  result is something only this app knows -- GATE-13 allows it).
* The days are a report list (date, conditions, high, low, precipitation), so a
  listener can arrow through them; Copy puts the summary, every day as a
  sentence, and the credits on the clipboard.
* Only the fields the chosen kind of lookup uses are shown, so Tab never stops
  on a field that does nothing.
* The data credits are shown under the list and are part of the summary text,
  so they are read and copied too.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from quill.core.weather import history_text
from quill.ui.dialog_contract import (
    apply_modal_ids,
    bind_close_button,
    set_accessible_name,
    show_modal_dialog,
)
from quill.ui.dpi import dip, dip_size
from quill.ui.surface_lifetime import surface_tasks

KINDS = (
    ("on_this_day", "On this day, over the years"),
    ("same_date", "Another date, over the years"),
    ("range", "A date range"),
)
_MONTHS = (
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
)  # fmt: skip
_COLUMNS = (("Date", 150), ("Conditions", 150), ("High", 60), ("Low", 60), ("Precipitation", 160))


def parse_iso_date(text: str) -> date | None:
    """'2024-06-01' -> date; anything else -> None."""
    try:
        return date.fromisoformat(text.strip())
    except ValueError:
        return None


def summary_lead(summary: str, sentences: int = 2) -> str:
    """The first sentences after the place line: the comparison with normal."""
    parts = [p.strip() for p in summary.split(". ") if p.strip()]
    lead = parts[1 : 1 + sentences] if len(parts) > 1 else parts[:1]
    text = ". ".join(lead)
    return text if text.endswith(".") or not text else text + "."


class WeatherHistoryDialog:
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
        open_day: Callable[[str, date | None], None] | None = None,
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
        self._open_day = open_day
        self._store = loc_store.load_locations(data_dir)
        self._settings = settings_mod.load_settings(data_dir)
        self._rows: list[Any] = []
        self._summary_text = ""
        self._request = 0
        self.dialog = wx.Dialog(
            parent, title="Weather History", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._task_manager = surface_tasks(task_manager, lambda: getattr(self, "dialog", None))
        dlg = self.dialog
        root = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(cols=2, vgap=dip(dlg, 6), hgap=dip(dlg, 8))
        grid.AddGrowableCol(1)

        # Each label is created BEFORE its control: Windows screen readers and
        # access keys both take a control's name from the static text just
        # before it in creation order.
        def label(text: str) -> Any:
            static = wx.StaticText(dlg, label=text)
            grid.Add(static, 0, wx.ALIGN_CENTER_VERTICAL)
            return static

        def place(control: Any) -> None:
            grid.Add(control, 1, wx.EXPAND)

        label("&Place:")
        self._place = wx.Choice(dlg, choices=[loc.label for loc in self._store.locations])
        self._place.SetHelpText(
            "The saved place to look up. Add places with Weather, Add Location."
        )
        place(self._place)
        primary = self._store.primary()
        if primary is not None and primary in self._store.locations:
            self._place.SetSelection(self._store.locations.index(primary))
        elif self._store.locations:
            self._place.SetSelection(0)

        label("&Kind of lookup:")
        self._kind = wx.Choice(dlg, choices=[text for _key, text in KINDS])
        self._kind.SetHelpText(
            "What to look up: today's date over many years, another calendar date "
            "over many years, or every day between two dates."
        )
        place(self._kind)
        self._kind.SetSelection(0)

        today = date.today()
        self._month_label = label("&Month:")
        self._month = wx.Choice(dlg, choices=list(_MONTHS))
        self._month.SetHelpText("The month of the calendar date to look up.")
        place(self._month)
        self._month.SetSelection(today.month - 1)

        self._day_label = label("&Day:")
        self._day = wx.SpinCtrl(dlg, min=1, max=31, initial=today.day)
        self._day.SetHelpText("The day of the month, 1 to 31.")
        place(self._day)

        self._years_label = label("&Years to look back:")
        years = max(1, min(85, self._settings.history_years))
        self._years = wx.SpinCtrl(dlg, min=1, max=85, initial=years)
        self._years.SetHelpText(
            "How many years to look back, 1 to 85. Data goes back to 1940. Every year "
            "looked up is saved, so a second look costs nothing."
        )
        place(self._years)

        self._start_label = label("&From (year-month-day):")
        self._start = wx.TextCtrl(dlg, value=today.replace(day=1).isoformat())
        self._start.SetHelpText(
            "The first day of the range, written year-month-day, like 2024-06-01."
        )
        place(self._start)

        self._end_label = label("&To (year-month-day):")
        self._end = wx.TextCtrl(dlg, value=today.isoformat())
        self._end.SetHelpText(
            "The last day of the range, written year-month-day. A range can be up to a year."
        )
        place(self._end)
        root.Add(grid, 0, wx.EXPAND | wx.ALL, dip(dlg, 12))

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._go = wx.Button(dlg, wx.ID_ANY, "Look &Up")
        self._go.SetDefault()
        self._go.SetHelpText("Look up the weather for these dates. Enter does the same.")
        buttons.Add(self._go, 0, wx.RIGHT, dip(dlg, 6))
        self._goto = wx.Button(dlg, wx.ID_ANY, "&Go to Date...")
        self._goto.SetHelpText(
            "Open Weather on a Past Date for the day chosen in the list, or for today, to "
            "read that one day hour by hour. Ctrl+G does the same, and so does Enter on "
            "a day in the list."
        )
        buttons.Add(self._goto)
        root.Add(buttons, 0, wx.LEFT | wx.RIGHT, dip(dlg, 12))

        self._status = wx.StaticText(dlg, label="")
        root.Add(self._status, 0, wx.EXPAND | wx.ALL, dip(dlg, 12))

        root.Add(wx.StaticText(dlg, label="&Summary:"), 0, wx.LEFT | wx.RIGHT, dip(dlg, 12))
        self._summary = wx.TextCtrl(
            dlg,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            size=dip_size(dlg, 600, 140),
        )
        set_accessible_name(self._summary, "Weather history summary")
        self._summary.SetHelpText(
            "The lookup in plain words: how the day compares with normal, the records, "
            "and how often it rained or snowed. Use the arrow keys to read it."
        )
        root.Add(self._summary, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, dip(dlg, 12))

        root.Add(
            wx.StaticText(dlg, label="Day &by day:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, dip(dlg, 12)
        )
        self._list = wx.ListCtrl(
            dlg, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=dip_size(dlg, 600, 180)
        )
        for i, (title, width) in enumerate(_COLUMNS):
            self._list.InsertColumn(i, title, width=dip(dlg, width))
        set_accessible_name(self._list, "Day by day")
        self._list.SetHelpText(
            "One row a day: the date, the conditions, the high, the low and the "
            "precipitation, newest first. Use the arrow keys to move between days, and "
            "Enter to read a day hour by hour."
        )
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, dip(dlg, 12))

        self._credits = wx.StaticText(dlg, label=history_text.CREDIT_OPEN_METEO)
        root.Add(self._credits, 0, wx.EXPAND | wx.ALL, dip(dlg, 12))

        bottom = wx.BoxSizer(wx.HORIZONTAL)
        bottom.AddStretchSpacer()
        copy_btn = wx.Button(dlg, wx.ID_ANY, "&Copy")
        copy_btn.SetHelpText("Copy the summary, every day and the data credits.")
        bottom.Add(copy_btn, 0, wx.RIGHT, dip(dlg, 6))
        close_btn = wx.Button(dlg, wx.ID_CANCEL, "Close")
        close_btn.SetHelpText("Close Weather History. Escape does the same.")
        bottom.Add(close_btn)
        root.Add(bottom, 0, wx.EXPAND | wx.ALL, dip(dlg, 12))

        dlg.SetSizer(root)
        dlg.SetMinSize(dip_size(dlg, 640, 600))
        self._kind.Bind(wx.EVT_CHOICE, lambda _e: self._show_fields())
        self._go.Bind(wx.EVT_BUTTON, lambda _e: self.look_up())
        copy_btn.Bind(wx.EVT_BUTTON, lambda _e: self.copy())
        self._goto.Bind(wx.EVT_BUTTON, lambda _e: self.go_to_date())
        # After the event, so a double-click's second release cannot land in the
        # list once the nested window has closed.
        self._list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _e: wx.CallAfter(self.go_to_date))
        dlg.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self._goto.Show(open_day is not None)
        bind_close_button(dlg, close_btn, modeless=False)
        self._show_fields()
        root.Fit(dlg)
        if not self._store.locations:
            self._go.Disable()
            self._status.SetLabel("No saved places yet. Add one with Weather, Add Location.")

    # -- fields ------------------------------------------------------------------

    def kind(self) -> str:
        return KINDS[max(0, self._kind.GetSelection())][0]

    def _show_fields(self) -> None:
        kind = self.kind()
        for widgets, visible in (
            ((self._month_label, self._month, self._day_label, self._day), kind == "same_date"),
            ((self._years_label, self._years), kind != "range"),
            ((self._start_label, self._start, self._end_label, self._end), kind == "range"),
        ):
            for widget in widgets:
                widget.Show(visible)
        self.dialog.Layout()

    def build_query(self) -> Any:
        """The Query for the fields as they are, or a sentence saying what is wrong
        (and focus moved to the field to fix)."""
        from quill.core.weather.history_service import Query

        kind = self.kind()
        if kind == "range":
            start = parse_iso_date(self._start.GetValue())
            end = parse_iso_date(self._end.GetValue())
            if start is None:
                self._start.SetFocus()
                return "The From date needs to be year-month-day, like 2024-06-01."
            if end is None:
                self._end.SetFocus()
                return "The To date needs to be year-month-day, like 2024-06-30."
            return Query("range", start=start, end=end)
        years = self._years.GetValue()
        if kind == "on_this_day":
            return Query("on_this_day", years=years)
        month, day = self._month.GetSelection() + 1, self._day.GetValue()
        try:
            date(2024, month, day)
        except ValueError:
            self._day.SetFocus()
            return f"{_MONTHS[month - 1]} has no day {day}."
        return Query("same_date", month=month, day=day, years=years)

    # -- lookup ------------------------------------------------------------------

    def look_up(self) -> None:
        from quill.core.weather import history_service

        index = self._place.GetSelection()
        if index < 0 or index >= len(self._store.locations):
            self._say("Choose a place first.")
            return
        query = self.build_query()
        if isinstance(query, str):
            # Focus has moved to the field to fix; speak after the reader has
            # announced that field, or it cuts the explanation off.
            self._status.SetLabel(query)
            self._wx.CallLater(250, self._announce, query)
            return
        location = self._store.locations[index]
        self._save_years(query)
        self._request = request = self._request + 1
        self._say(f"Looking up weather history for {location.label}.")
        unit = self._settings.temperature_unit
        data_dir, health, safe_mode = self._data_dir, self._health, self._safe_mode

        def _work(**_kwargs: Any) -> object:
            try:
                return history_service.look_up(
                    query,
                    place=location.label,
                    latitude=location.latitude,
                    longitude=location.longitude,
                    unit=unit,
                    data_dir=data_dir,
                    health=health,
                    safe_mode=safe_mode,
                )
            except history_service.history.HistoryError as exc:
                return exc

        if self._task_manager is None:
            self._landed(request, _work())
            return
        # The task manager already delivers on the UI thread, checking the window
        # is alive at that moment; another CallAfter hop would make that stale.
        self._task_manager.submit(
            "weather-history",
            _work,
            on_success=lambda _op, result: self._landed(request, result),
            on_failure=lambda _op, exc: self._landed(request, exc),
        )

    def _save_years(self, query: Any) -> None:
        if query.kind == "range" or query.years == self._settings.history_years:
            return
        from quill.core.weather import settings as settings_mod

        self._settings.history_years = query.years
        try:
            settings_mod.save_settings(self._data_dir, self._settings)
        except OSError:
            pass

    def _landed(self, request: int, result: object) -> None:
        from quill.core.weather.history_service import Lookup

        if request != self._request:
            return  # an older lookup; the newest one owns the window
        self._on_health_changed()
        if not isinstance(result, Lookup):
            self._clear()  # so the last answer is never read as this one's
            self._say(f"Could not look that up. {result}")
            return
        self.show_result(result)
        found = len(result.rows)
        status = f"{found} day{'s' if found != 1 else ''} found."
        self._status.SetLabel(status)
        # The answer in brief; the whole summary is in the Summary box (Alt+S).
        self._announce(f"{status} {summary_lead(result.summary)}")

    def _clear(self) -> None:
        self._rows = []
        self._summary_text = ""
        self._summary.SetValue("")
        self._list.DeleteAllItems()

    def show_result(self, result: Any) -> None:
        self._rows = list(result.rows)
        self._summary_text = f"{result.summary}\n\nSources: {result.credits}"
        self._summary.SetValue(self._summary_text)
        self._summary.SetInsertionPoint(0)
        self._credits.SetLabel(result.credits)
        self._credits.Wrap(dip(self.dialog, 600))
        self._list.DeleteAllItems()
        for i, record in enumerate(self._rows):
            cells = history_text.row_cells(record, result.unit)
            index = self._list.InsertItem(i, cells[0])
            for col, value in enumerate(cells[1:], start=1):
                self._list.SetItem(index, col, value)
        for col in range(len(_COLUMNS)):
            self._list.SetColumnWidth(col, self._wx.LIST_AUTOSIZE_USEHEADER)
        # Selecting under the user's own focus would make the reader speak a row
        # over the result, so only an unfocused list gets its first row picked.
        if self._rows and not self._list.HasFocus():
            self._list.Select(0)
            self._list.Focus(0)
        self._unit = result.unit
        self.dialog.Layout()

    def copy_text(self) -> str:
        unit = getattr(self, "_unit", self._settings.temperature_unit)
        lines = [self._summary_text] if self._summary_text else []
        lines.extend(history_text.row_sentence(r, unit) for r in self._rows)
        return "\n".join(lines)

    def copy(self) -> None:
        text = self.copy_text()
        if not text:
            self._announce("Nothing to copy yet. Look something up first.")
            return
        wx = self._wx
        clipboard: Any = wx.TheClipboard
        if clipboard.Open():
            try:
                clipboard.SetData(wx.TextDataObject(text))
            finally:
                clipboard.Close()
            self._announce("Weather history copied.")
        else:
            self._announce("Could not open the clipboard.")

    def _on_char_hook(self, event: Any) -> None:
        code = event.GetKeyCode()
        wanted = event.ControlDown() and not event.AltDown() and code in (ord("G"), ord("g"))
        if wanted and self._open_day is not None:
            self.go_to_date()
            return
        event.Skip()

    def go_to_date(self) -> None:
        """Weather on a Past Date for the chosen row's day (or today) and place."""
        if self._open_day is None:
            return
        index = self._place.GetSelection()
        locations = self._store.locations
        place_id = locations[index].id if 0 <= index < len(locations) else ""
        row = self._list.GetFirstSelected()
        day = date.fromisoformat(self._rows[row].date) if 0 <= row < len(self._rows) else None
        self._open_day(place_id, day)

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
        try:
            show_modal_dialog(self.dialog, "Weather History", announce=self._announce)
        finally:
            self.dialog.Destroy()
