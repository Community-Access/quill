"""Weather on a Past Date, the lists half: the span of days to browse, the
recent dates, and Copy and Save Range. Split from ``past_date_dialog`` under
GATE-11; mixed into :class:`~quill.ui.weather.past_date_dialog.PastDateDialog`,
whose ``__init__`` builds every control these methods use.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from quill.core.weather import date_query, past_day_text, recent_dates


def short_note(note: str) -> str:
    """'Read as March 4, 2011, month first, as your system writes dates.' ->
    'Read month first, as your system writes dates.' (the date was just said)."""
    if note.startswith("Read as ") and ", " in note:
        parts = note.split(", ")
        tail = ", ".join(p for p in parts[2:] if p)
        return f"Read {tail}" if tail else note
    return note


def span_name(start: date, end: date) -> str:
    """'March 2011' or '2011' for the span lists."""
    import calendar

    if start.month == end.month and start.year == end.year:
        return f"{calendar.month_name[start.month]} {start.year}"
    if start.year == end.year:
        return str(start.year)
    return f"{start.isoformat()} to {end.isoformat()}"


class PastDateListsMixin:
    """Spans, recent dates, copy and save for :class:`PastDateDialog`."""

    _wx: Any
    dialog: Any
    _span: Any
    _span_label: Any
    _span_rows: list[Any]
    _recent: list[Any]
    _recent_list: Any
    _store: Any
    _units: Any
    _data_dir: Any
    _today: date
    _order: str
    _health: Any
    _task_manager: Any
    _status: Any
    _request: int
    _day: Any
    _day_text: str
    _credits: str
    current: date | None
    _back: Any
    _fwd: Any
    _last_year: Any
    _next_year: Any
    _copy: Any

    def _location(self) -> Any: ...
    def _select_place(self, place_id: str) -> None: ...
    def _say(self, text: str) -> None: ...
    def _announce(self, text: str) -> None: ...
    def _on_health_changed(self) -> None: ...
    def show_day(self, day: date, *, announce_move: str, note: str = "") -> None: ...

    # -- spans ---------------------------------------------------------------------

    def _show_span(self, visible: bool) -> None:
        self._span_label.Show(visible)
        self._span.Show(visible)
        self.dialog.Layout()

    def show_span(self, start: date, end: date) -> None:
        """List every day from *start* to *end* (a year or a month) to browse."""
        from quill.core.weather import history_service

        location = self._location()
        if location is None:
            return
        self._request = request = self._request + 1
        self._status.SetLabel("Getting the days...")
        query = history_service.Query("range", start=start, end=end)
        unit, data_dir, health = self._units.temperature, self._data_dir, self._health
        today = self._today

        def _work(**_kwargs: Any) -> object:
            return history_service.look_up(
                query,
                place=location.label,
                latitude=location.latitude,
                longitude=location.longitude,
                unit=unit,
                data_dir=data_dir,
                today=today,
                health=health,
            )

        def landed(result: object) -> None:
            self._span_landed(request, start, end, result)

        if self._task_manager is None:
            landed(_work())
            return
        self._task_manager.submit(
            "weather-past-span",
            _work,
            on_success=lambda _op, result: landed(result),
            on_failure=lambda _op, exc: landed(exc),
        )

    def _span_landed(self, request: int, start: date, end: date, result: object) -> None:
        from quill.core.weather import history_text
        from quill.core.weather.history_service import Lookup

        if request != self._request:
            return
        self._on_health_changed()
        if not isinstance(result, Lookup):
            self._say(f"Could not get those days. {result}")
            return
        self._span_rows = sorted(result.rows, key=lambda r: r.date)
        self._span.DeleteAllItems()
        for i, record in enumerate(self._span_rows):
            cells = history_text.row_cells(record, result.unit)
            index = self._span.InsertItem(i, cells[0])
            for col, value in enumerate(cells[1:], start=1):
                self._span.SetItem(index, col, value)
        self._show_span(True)
        count = len(self._span_rows)
        what = f"{date_query.long_date(start)} to {date_query.long_date(end)}"
        self._status.SetLabel(f"{count} days, {what}.")
        if not count:
            self._say(f"No days could be shown for {what}. {result.summary}")
            return
        self._span_label.SetLabel(f"Day&s in {span_name(start, end)}:")
        self._span.Select(0)
        self._span.Focus(0)
        self._span.SetFocus()
        self._wx.CallLater(250, self._announce, f"{count} days, {what}.")

    def _open_span_row(self, index: int) -> None:
        if 0 <= index < len(self._span_rows):
            self.show_day(date.fromisoformat(self._span_rows[index].date), announce_move="")

    # -- recent dates --------------------------------------------------------------

    def _fill_recent(self) -> None:
        labels = []
        for entry in self._recent:
            when = date_query.long_date(date.fromisoformat(entry.date))
            labels.append(f"{when}, {entry.place_label}" if entry.place_label else when)
        # Kept enabled with a placeholder, so Alt+R and Tab still arrive.
        self._recent_list.Set(labels or ["No recent dates yet."])
        if labels and self._recent_list.HasFocus():
            self._recent_list.SetSelection(0)  # the day just opened

    def _remember(self, day: date, location: Any) -> None:
        entry = recent_dates.RecentDate(day.isoformat(), location.id, location.label)
        self._recent = recent_dates.remember(self._recent, entry)
        recent_dates.save(self._data_dir, self._recent)
        self._fill_recent()

    def _open_recent(self) -> None:
        index = self._recent_list.GetSelection()
        if not 0 <= index < len(self._recent):
            return
        entry = self._recent[index]
        if not any(loc.id == entry.place_id for loc in self._store.locations):
            self._say(f"{entry.place_label or 'That place'} is no longer saved; showing it here.")
        self._select_place(entry.place_id)
        self.show_day(date.fromisoformat(entry.date), announce_move="")

    # -- copy and save -------------------------------------------------------------

    def _sync_buttons(self) -> None:
        have = self.current is not None
        for button in (self._back, self._fwd, self._last_year, self._next_year, self._copy):
            button.Enable(have)

    def copy_text(self) -> str:
        if self._day is None:
            return self._day_text
        location = self._location()
        place = location.label if location is not None else ""
        lines = self._day_text.splitlines()
        compared = next((ln for ln in lines if ln.startswith("Compared with normal")), "")
        return past_day_text.day_text(
            self._day, place, self._units, compared=compared, credits=self._credits
        )

    def copy(self) -> None:
        text = self.copy_text()
        if not text:
            self._announce("Nothing to copy yet. Go to a date first.")
            return
        wx = self._wx
        clipboard: Any = wx.TheClipboard
        if clipboard.Open():
            try:
                clipboard.SetData(wx.TextDataObject(text))
            finally:
                clipboard.Close()
            self._announce("Day copied.")
        else:
            self._announce("Could not open the clipboard.")

    def save_range(self) -> None:
        from quill.ui.weather.save_range_dialog import SaveRangeDialog

        location = self._location()
        if location is None:
            return
        SaveRangeDialog(
            self.dialog,
            location=location,
            data_dir=self._data_dir,
            units=self._units,
            today=self._today,
            order=self._order,
            start=self.current,
            task_manager=self._task_manager,
            announce_cb=self._announce,
            health=self._health,
        ).show()
        self._on_health_changed()
