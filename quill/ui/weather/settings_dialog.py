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

        label("&Extended daily outlook (days, 0 = off):")
        self._daily_days = wx.SpinCtrl(
            self.dialog, min=0, max=16, initial=settings.daily_outlook_days
        )
        set_accessible_name(
            self._daily_days, "Extended daily outlook length in days, 0 turns it off"
        )
        grid.Add(self._daily_days, 0)

        label("Ho&urly forecast (hours, 0 = off):")
        self._hourly_hours = wx.SpinCtrl(self.dialog, min=0, max=48, initial=settings.hourly_hours)
        set_accessible_name(self._hourly_hours, "Hourly forecast length in hours, 0 turns it off")
        grid.Add(self._hourly_hours, 0)

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
            wx.StaticText(
                self.dialog,
                label="Current-conditions details to include (temperature and sky always show):",
            ),
            0,
            wx.LEFT | wx.TOP,
            12,
        )
        self._detail_checks: dict[str, Any] = {}
        for attr, text in (
            ("show_feels_like", "Feels-&like temperature"),
            ("show_humidity", "H&umidity"),
            ("show_dew_point", "Dew &point"),
            ("show_wind", "&Wind and gusts"),
            ("show_cloud_cover", "&Cloud cover"),
            ("show_pressure", "Barometric pr&essure"),
            ("show_visibility", "&Visibility"),
            ("show_precip_chance", "Chance of pre&cipitation today"),
            ("show_sunrise_sunset", "Sunrise and sun&set"),
            ("show_moon", "&Moon phase, moonrise and moonset"),
            ("show_uv_index", "Ultra&violet index"),
            ("show_air_quality", "&Air quality"),
            ("show_local_time", "Current local &time at the location"),
        ):
            self._detail_checks[attr] = self._check(root, text, getattr(settings, attr))

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

        # -- alert sound --
        self._alert_sound = self._check(
            root, "Play a &sound when a new alert is announced", settings.alert_sound_enabled
        )
        sound_row = wx.BoxSizer(wx.HORIZONTAL)
        sound_row.Add(
            wx.StaticText(self.dialog, label="Alert soun&d:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._alert_sound_path = wx.TextCtrl(self.dialog, style=wx.TE_READONLY)
        set_accessible_name(self._alert_sound_path, "Chosen alert sound file")
        self._alert_sound_path.SetValue(settings.alert_sound_path or "(default chime)")
        self._alert_sound_value = settings.alert_sound_path
        sound_row.Add(self._alert_sound_path, 1, wx.EXPAND | wx.RIGHT, 6)
        choose_btn = wx.Button(self.dialog, label="C&hoose...")
        play_btn = wx.Button(self.dialog, label="&Play")
        default_btn = wx.Button(self.dialog, label="Use De&fault")
        for b in (choose_btn, play_btn, default_btn):
            sound_row.Add(b, 0, wx.RIGHT, 4)
        root.Add(sound_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        choose_btn.Bind(wx.EVT_BUTTON, lambda _e: self._choose_alert_sound())
        play_btn.Bind(wx.EVT_BUTTON, lambda _e: self._preview_alert_sound())
        default_btn.Bind(wx.EVT_BUTTON, lambda _e: self._reset_alert_sound())

        repeat_row = wx.BoxSizer(wx.HORIZONTAL)
        repeat_row.Add(
            wx.StaticText(self.dialog, label="P&lay the alert sound this many times:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._alert_sound_repeat = wx.SpinCtrl(
            self.dialog, min=1, max=10, initial=settings.alert_sound_repeat
        )
        set_accessible_name(self._alert_sound_repeat, "Number of times to play the alert sound")
        repeat_row.Add(self._alert_sound_repeat, 0)
        root.Add(repeat_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)

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

    # -- alert sound --

    def _choose_alert_sound(self) -> None:
        wx = self._wx
        dlg = wx.FileDialog(
            self.dialog,
            "Choose an alert sound",
            wildcard="Sound files (*.wav)|*.wav|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        try:
            if dlg.ShowModal() == wx.ID_OK:
                self._alert_sound_value = dlg.GetPath()
                self._alert_sound_path.SetValue(self._alert_sound_value)
                self._announce("Alert sound chosen.")
        finally:
            dlg.Destroy()

    def _reset_alert_sound(self) -> None:
        self._alert_sound_value = ""
        self._alert_sound_path.SetValue("(default chime)")
        self._announce("Using the default alert sound.")

    def _preview_alert_sound(self) -> None:
        """Play the currently-selected sound (or the default) so the user can
        hear it before saving."""
        from quill.platform import alert_sound

        alert_sound.play_alert_sound(self._alert_sound_value, self._alert_sound_repeat.GetValue())
        self._announce("Playing the alert sound.")

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
        s.daily_outlook_days = self._daily_days.GetValue()
        s.hourly_hours = self._hourly_hours.GetValue()
        for attr, check in self._detail_checks.items():
            setattr(s, attr, check.GetValue())
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
        s.alert_sound_enabled = self._alert_sound.GetValue()
        s.alert_sound_path = self._alert_sound_value
        s.alert_sound_repeat = self._alert_sound_repeat.GetValue()
        settings_mod.save_settings(self._data_dir, s)
        self._saved = True
        self._announce("Weather settings saved.")
        if self.dialog.IsModal():
            self.dialog.EndModal(self._wx.ID_OK)
