"""Weather Center -- the accessible, text-only weather workspace (PRD 5.1).

One dialog per open. It loads the saved locations and settings, fetches the
primary (or a requested) location off the UI thread, and lays the result out as
native, screen-reader-first controls in the PRD's reading order: active alerts
first (a list you arrow through, with full official text below), then current
conditions, then the period forecast (also a list, with each period's detailed
text below), then a source/freshness status line. A Location chooser switches
places; Refresh re-pulls; Add Location and Settings open their own dialogs.

Speech is a later phase -- but every string shown here comes from
``core/weather/render.py``, so when speech lands it speaks exactly this text.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.weather import locations as loc_store
from quill.core.weather import nws, render
from quill.core.weather import settings as settings_mod
from quill.core.weather.models import WeatherLocation, WeatherReport
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name


def _alert_list_label(alert: Any) -> str:
    """One-line list entry: event, area, tier, and when it expires."""
    bits = [alert.event]
    if alert.area_description:
        bits.append(alert.area_description.split(";")[0].strip())
    bits.append(alert.tier)
    return " -- ".join(b for b in bits if b)


def _alert_detail_text(alert: Any) -> str:
    """The full official alert: headline, instructions, description, timing."""
    lines = [alert.headline or alert.event]
    lines.append(
        f"Severity {alert.severity or 'Unknown'}, urgency {alert.urgency or 'Unknown'}, "
        f"certainty {alert.certainty or 'Unknown'}."
    )
    if alert.area_description:
        lines.append(f"Area: {alert.area_description}")
    if alert.effective or alert.expires:
        lines.append(f"In effect {alert.effective or '?'} to {alert.expires or '?'}.")
    if alert.instruction:
        lines.append("")
        lines.append("Instructions: " + alert.instruction)
    if alert.description:
        lines.append("")
        lines.append(alert.description)
    if alert.sender_name:
        lines.append("")
        lines.append(f"Issued by {alert.sender_name}.")
    return "\n".join(lines)


class WeatherCenterDialog:
    """Accessible text weather for one location at a time."""

    def __init__(
        self,
        parent: object,
        *,
        data_dir: Path,
        task_manager: object,
        safe_mode: bool,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._data_dir = data_dir
        self._task_manager = task_manager
        self._safe_mode = safe_mode
        self._announce = announce_cb or (lambda _m: None)
        self._store = loc_store.load_locations(data_dir)
        self._settings = settings_mod.load_settings(data_dir)
        self._report: WeatherReport | None = None
        self._shown_alerts: list[Any] = []

        self.dialog = wx.Dialog(
            parent, title="Weather Center", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((620, 560))
        root = wx.BoxSizer(wx.VERTICAL)

        # -- location row --
        loc_row = wx.BoxSizer(wx.HORIZONTAL)
        loc_row.Add(
            wx.StaticText(self.dialog, label="&Location:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._location_choice = wx.Choice(self.dialog)
        set_accessible_name(self._location_choice, "Weather location")
        loc_row.Add(self._location_choice, 1, wx.EXPAND | wx.RIGHT, 6)
        self._refresh_btn = wx.Button(self.dialog, label="&Refresh")
        self._add_btn = wx.Button(self.dialog, label="&Add Location...")
        self._settings_btn = wx.Button(self.dialog, label="&Settings...")
        for b in (self._refresh_btn, self._add_btn, self._settings_btn):
            loc_row.Add(b, 0, wx.RIGHT, 4)
        root.Add(loc_row, 0, wx.EXPAND | wx.ALL, 10)

        # -- active alerts --
        self._alerts_label = wx.StaticText(self.dialog, label="Active &Alerts:")
        root.Add(self._alerts_label, 0, wx.LEFT | wx.RIGHT, 10)
        self._alerts_list = wx.ListBox(self.dialog)
        set_accessible_name(self._alerts_list, "Active weather alerts")
        root.Add(self._alerts_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self._alert_detail = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        set_accessible_name(self._alert_detail, "Selected alert, full official text")
        root.Add(self._alert_detail, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # -- current conditions --
        root.Add(
            wx.StaticText(self.dialog, label="&Current conditions:"), 0, wx.LEFT | wx.RIGHT, 10
        )
        self._current = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        set_accessible_name(self._current, "Current conditions")
        self._current.SetMinSize((-1, 48))
        root.Add(self._current, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # -- forecast --
        root.Add(wx.StaticText(self.dialog, label="&Forecast:"), 0, wx.LEFT | wx.RIGHT, 10)
        self._forecast_list = wx.ListBox(self.dialog)
        set_accessible_name(self._forecast_list, "Forecast periods")
        root.Add(self._forecast_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self._period_detail = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        set_accessible_name(self._period_detail, "Selected forecast period, details")
        self._period_detail.SetMinSize((-1, 60))
        root.Add(self._period_detail, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # -- status + close --
        self._status = wx.TextCtrl(self.dialog, style=wx.TE_READONLY)
        set_accessible_name(self._status, "Weather source and freshness status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        btn_row.AddStretchSpacer()
        btn_row.Add(wx.Button(self.dialog, wx.ID_CANCEL, "Close"))
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        self._location_choice.Bind(wx.EVT_CHOICE, lambda _e: self._on_location_chosen())
        self._alerts_list.Bind(wx.EVT_LISTBOX, lambda _e: self._on_alert_selected())
        self._forecast_list.Bind(wx.EVT_LISTBOX, lambda _e: self._on_period_selected())
        self._refresh_btn.Bind(wx.EVT_BUTTON, lambda _e: self._refresh())
        self._add_btn.Bind(wx.EVT_BUTTON, lambda _e: self._add_location())
        self._settings_btn.Bind(wx.EVT_BUTTON, lambda _e: self._open_settings())

        self._reload_location_choice()

    # -- lifecycle --------------------------------------------------------------

    def show(self, *, focus_alerts: bool = False) -> None:
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, cancel_id=self._wx.ID_CANCEL)
        from quill.ui.dialog_contract import show_modal_dialog

        if self._store.locations:
            if self._settings.refresh_on_open:
                self._refresh()
            if focus_alerts:
                self._alerts_list.SetFocus()
        else:
            self._status.SetValue("No locations yet. Choose Add Location to begin.")
            self._announce("No weather locations yet. Choose Add Location to begin.")
        try:
            show_modal_dialog(self.dialog, "Weather Center", announce=self._announce)
        finally:
            self.dialog.Destroy()

    # -- location chooser -------------------------------------------------------

    def _reload_location_choice(self) -> None:
        self._location_choice.Set([loc.label for loc in self._store.locations])
        primary = self._store.primary()
        if primary is not None:
            index = self._store.locations.index(primary)
            self._location_choice.SetSelection(index)

    def _current_location(self) -> WeatherLocation | None:
        index = self._location_choice.GetSelection()
        if 0 <= index < len(self._store.locations):
            return self._store.locations[index]
        return self._store.primary()

    def _on_location_chosen(self) -> None:
        location = self._current_location()
        if location is not None:
            self._store.set_primary(location.id)
            loc_store.save_locations(self._data_dir, self._store)
            self._refresh()

    # -- fetch ------------------------------------------------------------------

    def _refresh(self) -> None:
        location = self._current_location()
        if location is None:
            return
        self._status.SetValue(f"Loading weather for {location.label}...")
        self._announce(f"Loading weather for {location.label}.")

        def _work(**_kwargs: Any) -> object:
            try:
                return nws.fetch_report(location, safe_mode=self._safe_mode)
            except nws.WeatherError as exc:
                return exc

        def _ok(_op: str, result: object) -> None:
            self._wx.CallAfter(self._render_report, location, result)

        self._task_manager.submit("weather-fetch", _work, on_success=_ok, on_failure=None)

    def _render_report(self, location: WeatherLocation, result: object) -> None:
        if isinstance(result, nws.WeatherError):
            self._status.SetValue(f"Could not load weather: {result}")
            self._announce(f"Could not load weather. {result}")
            return
        if not isinstance(result, WeatherReport):
            return
        self._report = result
        self._reload_location_choice()  # a resolved name may have filled in

        alerts = render.filtered_alerts(result, self._settings)
        self._shown_alerts = alerts
        self._alerts_list.Set([_alert_list_label(a) for a in alerts] or ["No active alerts."])
        self._alerts_label.SetLabel(
            f"Active &Alerts ({len(alerts)}):" if alerts else "Active &Alerts (none):"
        )
        self._alert_detail.SetValue(_alert_detail_text(alerts[0]) if alerts else "")

        if result.current is not None:
            self._current.SetValue(render.current_conditions_line(result.current, self._settings))
        else:
            self._current.SetValue("Current conditions are unavailable right now.")

        periods = result.periods[: self._settings.forecast_period_count]
        self._forecast_list.Set(
            [
                f"{p.name}: {p.temperature} deg {p.temperature_unit}, {p.short_forecast}"
                for p in periods
            ]
            or ["Forecast unavailable."]
        )
        self._period_detail.SetValue(
            periods[0].detailed_forecast
            if periods and self._settings.show_detailed_forecast
            else ""
        )
        self._status.SetValue(self._status_line(result))

        n = len(alerts)
        summary = f"{location.label}. "
        summary += (
            "No active alerts. "
            if n == 0
            else (f"{n} active alert{'' if n == 1 else 's'}; highest {alerts[0].event}. ")
        )
        if result.current is not None:
            summary += render.current_conditions_line(result.current, self._settings)
        if self._settings.announce_alert_count_on_open:
            self._announce(summary)

    def _status_line(self, report: WeatherReport) -> str:
        bits = [f"Source: National Weather Service office {report.office or '?'}"]
        if report.forecast_zone:
            bits.append(f"zone {report.forecast_zone}")
        if report.current and report.current.station_id:
            bits.append(f"observed at {report.current.station_id}")
        for note in report.notes:
            bits.append(note)
        return " -- ".join(bits)

    # -- selection --------------------------------------------------------------

    def _on_alert_selected(self) -> None:
        index = self._alerts_list.GetSelection()
        if 0 <= index < len(self._shown_alerts):
            self._alert_detail.SetValue(_alert_detail_text(self._shown_alerts[index]))

    def _on_period_selected(self) -> None:
        if self._report is None:
            return
        index = self._forecast_list.GetSelection()
        periods = self._report.periods[: self._settings.forecast_period_count]
        if 0 <= index < len(periods):
            self._period_detail.SetValue(periods[index].detailed_forecast)

    # -- sub-dialogs ------------------------------------------------------------

    def _add_location(self) -> None:
        from quill.ui.weather.add_location_dialog import AddLocationDialog

        dlg = AddLocationDialog(
            self.dialog,
            store=self._store,
            data_dir=self._data_dir,
            task_manager=self._task_manager,
            safe_mode=self._safe_mode,
            announce_cb=self._announce,
        )
        if dlg.show():
            self._reload_location_choice()
            self._refresh()

    def _open_settings(self) -> None:
        from quill.ui.weather.settings_dialog import WeatherSettingsDialog

        dlg = WeatherSettingsDialog(
            self.dialog,
            settings=self._settings,
            data_dir=self._data_dir,
            announce_cb=self._announce,
        )
        if dlg.show():
            self._settings = settings_mod.load_settings(self._data_dir)
            if self._report is not None:
                self._render_report(self._current_location() or self._report.location, self._report)
