"""Save Weather for a Date Range: every day between two dates, as CSV or text.

The From and To fields take the same dates the Date field does
(``date_query``), so "2011-03-01" and "March 31, 2011" both work. The days
are fetched on a worker thread through ``history_service`` (cached, and one
request per stretch of missing days), then written where the user chooses.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from quill.core.weather import date_query, past_day_text
from quill.ui.dialog_contract import (
    apply_modal_ids,
    bind_close_button,
    show_modal_dialog,
)
from quill.ui.dpi import dip
from quill.ui.surface_lifetime import surface_tasks

FORMATS = (("csv", "Spreadsheet (CSV)"), ("txt", "Plain text"))


class SaveRangeDialog:
    def __init__(
        self,
        parent: object,
        *,
        location: Any,
        data_dir: Path,
        units: past_day_text.Units,
        today: date,
        order: str,
        start: date | None,
        task_manager: Any,
        announce_cb: Callable[[str], None] | None = None,
        health: Any = None,
    ) -> None:
        import wx

        self._wx = wx
        self._location = location
        self._data_dir = data_dir
        self._units = units
        self._today = today
        self._order = order
        # Tied to this window: closing Save mid-fetch must not call back into it.
        self._task_manager = surface_tasks(task_manager, lambda: getattr(self, "dialog", None))
        self._announce = announce_cb or (lambda _m: None)
        self._health = health
        self.saved_path: str = ""
        self._trimmed = ""
        self.dialog = wx.Dialog(parent, title="Save Weather for a Date Range")
        dlg = self.dialog
        gap = dip(dlg, 12)
        root = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(cols=2, vgap=dip(dlg, 6), hgap=dip(dlg, 8))
        grid.AddGrowableCol(1)
        first = start.replace(day=1) if start else today.replace(day=1)
        grid.Add(wx.StaticText(dlg, label="&From:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._from = wx.TextCtrl(dlg, value=first.isoformat())
        self._from.SetHelpText(
            "The first day to save, such as 2011-03-01 or March 1, 2011. A range can be "
            "up to a year."
        )
        grid.Add(self._from, 1, wx.EXPAND)
        grid.Add(wx.StaticText(dlg, label="&To:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._to = wx.TextCtrl(dlg, value=(start or today).isoformat())
        self._to.SetHelpText("The last day to save, such as 2011-03-31 or yesterday.")
        grid.Add(self._to, 1, wx.EXPAND)
        grid.Add(wx.StaticText(dlg, label="F&ormat:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._format = wx.Choice(dlg, choices=[label for _ext, label in FORMATS])
        self._format.SetSelection(0)
        self._format.SetHelpText(
            "A spreadsheet file, one row a day with the units in the column names, or "
            "plain text, one sentence a day."
        )
        grid.Add(self._format, 1, wx.EXPAND)
        root.Add(grid, 0, wx.EXPAND | wx.ALL, gap)
        self._status = wx.StaticText(dlg, label="")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, gap)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        self._save = wx.Button(dlg, wx.ID_ANY, "&Save...")
        self._save.SetDefault()
        self._save.SetHelpText("Choose where to save the file, then save it.")
        buttons.Add(self._save, 0, wx.RIGHT, dip(dlg, 6))
        close_btn = wx.Button(dlg, wx.ID_CANCEL, "Close")
        close_btn.SetHelpText("Close without saving. Escape does the same.")
        buttons.Add(close_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, gap)
        dlg.SetSizer(root)
        root.Fit(dlg)
        self._save.Bind(wx.EVT_BUTTON, lambda _e: self.save())
        bind_close_button(dlg, close_btn, modeless=False)

    def _parse(self, field: Any, which: str) -> date | str:
        try:
            query = date_query.parse(field.GetValue(), today=self._today, order=self._order)
        except date_query.DateNotUnderstood as exc:
            return f"{which}: {exc.args[0]}"
        return query.start if which == "From" else query.end

    def dates(self) -> tuple[date, date] | str:
        """(start, end), or the sentence saying what is wrong."""
        start = self._parse(self._from, "From")
        if isinstance(start, str):
            return start
        end = self._parse(self._to, "To")
        if isinstance(end, str):
            return end
        if end < start:
            start, end = end, start
        if start > self._today:
            return "That range is in the future."
        notes = []
        if end > self._today:
            notes.append("Saved up to today.")
        if start < date_query.EARLIEST:
            notes.append("It starts on January 1, 1940, where the history begins.")
        self._trimmed = " ".join(notes)
        return max(start, date_query.EARLIEST), min(end, self._today)

    def save(self) -> None:
        wx = self._wx
        span = self.dates()
        if isinstance(span, str):
            self._say(span)
            return
        start, end = span
        ext, _label = FORMATS[max(0, self._format.GetSelection())]
        name = f"weather {self._location.label} {start.isoformat()} to {end.isoformat()}.{ext}"
        picker = wx.FileDialog(
            self.dialog,
            "Save weather for a date range",
            defaultFile="".join(c for c in name if c not in '\\/:*?"<>|'),
            wildcard="CSV files (*.csv)|*.csv" if ext == "csv" else "Text files (*.txt)|*.txt",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        try:
            if picker.ShowModal() != wx.ID_OK:
                return
            path = picker.GetPath()
        finally:
            picker.Destroy()
        self._say("Getting the days...")
        self._save.Disable()

        location, units, data_dir, today = self._location, self._units, self._data_dir, self._today
        health, trimmed = self._health, self._trimmed

        def _work(**_kwargs: Any) -> object:
            # The file is written here, so it is saved even if the window closes.
            text, count, problem = build_file(
                location, start, end, ext, units, data_dir, today, health=health
            )
            Path(path).write_text(text, encoding="utf-8", newline="")
            return count, " ".join(p for p in (problem, trimmed) if p)

        def landed(result: object) -> None:
            self._landed(path, result)

        if self._task_manager is None:
            landed(_work())
            return
        self._task_manager.submit(
            "weather-save-range",
            _work,
            on_success=lambda _op, result: landed(result),
            on_failure=lambda _op, exc: landed(exc),
        )

    def _landed(self, path: str, result: object) -> None:
        self._save.Enable()
        if not isinstance(result, tuple):
            self._say(f"Could not save the file. {result}")
            return
        count, problem = result
        self.saved_path = path
        tail = f" {problem}" if problem else ""
        self._say(f"Saved {count} day{'s' if count != 1 else ''} to {Path(path).name}.{tail}")

    def _say(self, text: str) -> None:
        self._status.SetLabel(text)
        self._status.Wrap(dip(self.dialog, 400))
        self.dialog.Layout()
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
            show_modal_dialog(self.dialog, "Save Weather for a Date Range", announce=self._announce)
        finally:
            self.dialog.Destroy()


def build_file(
    location: Any,
    start: date,
    end: date,
    ext: str,
    units: past_day_text.Units,
    data_dir: Path,
    today: date,
    *,
    health: Any = None,
) -> tuple[str, int, str]:
    """(file text, days, a sentence about any days that failed), off the UI thread."""
    from quill.core.weather import history_service

    result = history_service.look_up(
        history_service.Query("range", start=start, end=end),
        place=location.label,
        latitude=location.latitude,
        longitude=location.longitude,
        unit=units.temperature,
        data_dir=data_dir,
        today=today,
        health=health,
    )
    problem = ""
    if "could not be fetched" in result.summary:
        problem = "Some days could not be fetched and are not in the file."
    if ext == "csv":
        # CC BY asks for the credit wherever the data goes, so it is the last row.
        text = past_day_text.range_csv(result.rows, units) + f'"Sources: {result.credits}"\n'
    else:
        text = past_day_text.range_text(result.rows, location.label, units, credits=result.credits)
    return text, len(result.rows), problem
