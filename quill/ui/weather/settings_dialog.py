"""QUILL Weather settings dialog (PRD 13) -- the rich text-phase preferences:
units, Weather Now layout, alert filtering, refresh cadence, and Quick Weather
composition. Every control is native and labeled; OK normalizes and saves.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.weather.settings import (
    SEVERITY_FLOOR,
    TEMPERATURE_UNITS,
    WIND_UNITS,
    WeatherSettings,
)
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name

_SEVERITY_LABELS = {
    "all": "Show all alerts",
    "Minor": "Minor and above",
    "Moderate": "Moderate and above",
    "Severe": "Severe and above",
    "Extreme": "Extreme only",
}


class WeatherSettingsDialog:
    def __init__(
        self,
        parent: object,
        *,
        settings: WeatherSettings,
        data_dir: Path,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._settings = settings
        self._data_dir = data_dir
        self._announce = announce_cb or (lambda _m: None)
        self._saved = False

        self.dialog = wx.Dialog(
            parent, title="Weather Settings", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        root = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=10)
        grid.AddGrowableCol(1, 1)

        def label(text: str) -> None:
            grid.Add(self._wx.StaticText(self.dialog, label=text), 0, wx.ALIGN_CENTER_VERTICAL)

        # units
        label("&Temperature unit:")
        self._temp = wx.Choice(self.dialog, choices=["Fahrenheit", "Celsius"])
        set_accessible_name(self._temp, "Temperature unit")
        self._temp.SetSelection(TEMPERATURE_UNITS.index(settings.temperature_unit))
        grid.Add(self._temp, 0, wx.EXPAND)

        label("&Wind unit:")
        self._wind = wx.Choice(self.dialog, choices=list(WIND_UNITS))
        set_accessible_name(self._wind, "Wind speed unit")
        self._wind.SetSelection(WIND_UNITS.index(settings.wind_unit))
        grid.Add(self._wind, 0, wx.EXPAND)

        # forecast
        label("&Forecast periods to show:")
        self._periods = wx.SpinCtrl(
            self.dialog, min=1, max=14, initial=settings.forecast_period_count
        )
        set_accessible_name(self._periods, "Number of forecast periods to show")
        grid.Add(self._periods, 0)

        label("Alert &severity to show:")
        self._severity = wx.Choice(
            self.dialog, choices=[_SEVERITY_LABELS[s] for s in SEVERITY_FLOOR]
        )
        set_accessible_name(self._severity, "Minimum alert severity to show")
        self._severity.SetSelection(SEVERITY_FLOOR.index(settings.alert_severity_floor))
        grid.Add(self._severity, 0, wx.EXPAND)

        label("&Refresh every (minutes):")
        self._refresh = wx.SpinCtrl(self.dialog, min=1, max=180, initial=settings.refresh_minutes)
        set_accessible_name(self._refresh, "Auto-refresh interval in minutes")
        grid.Add(self._refresh, 0)

        root.Add(grid, 0, wx.EXPAND | wx.ALL, 12)

        # checkboxes
        self._detailed = self._check(
            root, "Show &detailed forecast text", settings.show_detailed_forecast
        )
        self._announce_open = self._check(
            root,
            "&Announce the summary when Weather Now opens",
            settings.announce_alert_count_on_open,
        )
        self._refresh_open = self._check(
            root, "Refresh &automatically when Weather Now opens", settings.refresh_on_open
        )

        root.Add(
            wx.StaticText(self.dialog, label="Quick Weather line includes:"),
            0,
            wx.LEFT | wx.TOP,
            12,
        )
        self._q_feels = self._check(
            root, "Feels-&like temperature", settings.quick_include_feels_like
        )
        self._q_wind = self._check(root, "Wi&nd", settings.quick_include_wind)
        self._q_humidity = self._check(root, "&Humidity", settings.quick_include_humidity)
        self._q_alerts = self._check(
            root, "Active alert &count", settings.quick_include_alert_count
        )
        self._q_age = self._check(root, "Data a&ge", settings.quick_include_data_age)

        root.Add(
            wx.StaticText(
                self.dialog,
                label="&Hide these alert events (one per line, exact event name):",
            ),
            0,
            wx.LEFT | wx.TOP,
            12,
        )
        self._muted = wx.TextCtrl(self.dialog, style=wx.TE_MULTILINE)
        set_accessible_name(self._muted, "Alert events to hide, one per line")
        self._muted.SetValue("\n".join(settings.muted_events))
        self._muted.SetMinSize((-1, 70))
        root.Add(self._muted, 1, wx.EXPAND | wx.ALL, 12)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        btn_row.AddStretchSpacer()
        ok = wx.Button(self.dialog, wx.ID_OK, "&Save")
        btn_row.Add(ok, 0, wx.RIGHT, 6)
        btn_row.Add(wx.Button(self.dialog, wx.ID_CANCEL, "Cancel"))
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 12)

        self.dialog.SetSizer(root)
        root.Fit(self.dialog)
        ok.Bind(wx.EVT_BUTTON, lambda _e: self._save())

    def _check(self, sizer: Any, text: str, value: bool) -> Any:
        box = self._wx.CheckBox(self.dialog, label=text)
        box.SetValue(value)
        sizer.Add(box, 0, self._wx.LEFT | self._wx.TOP, 12)
        return box

    def show(self) -> bool:
        """Modal; returns True if settings were saved."""
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="Save",
            cancel_id=self._wx.ID_CANCEL,
            cancel_label="Cancel",
        )
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self.dialog, "Weather Settings", announce=self._announce)
        finally:
            self.dialog.Destroy()
        return self._saved

    def _save(self) -> None:
        from quill.core.weather import settings as settings_mod

        s = self._settings
        s.temperature_unit = TEMPERATURE_UNITS[self._temp.GetSelection()]
        s.wind_unit = WIND_UNITS[self._wind.GetSelection()]
        s.forecast_period_count = self._periods.GetValue()
        s.alert_severity_floor = SEVERITY_FLOOR[self._severity.GetSelection()]
        s.refresh_minutes = self._refresh.GetValue()
        s.show_detailed_forecast = self._detailed.GetValue()
        s.announce_alert_count_on_open = self._announce_open.GetValue()
        s.refresh_on_open = self._refresh_open.GetValue()
        s.quick_include_feels_like = self._q_feels.GetValue()
        s.quick_include_wind = self._q_wind.GetValue()
        s.quick_include_humidity = self._q_humidity.GetValue()
        s.quick_include_alert_count = self._q_alerts.GetValue()
        s.quick_include_data_age = self._q_age.GetValue()
        s.muted_events = [
            line.strip() for line in self._muted.GetValue().splitlines() if line.strip()
        ]
        settings_mod.save_settings(self._data_dir, s)
        self._saved = True
        self._announce("Weather settings saved.")
        if self.dialog.IsModal():
            self.dialog.EndModal(self._wx.ID_OK)
