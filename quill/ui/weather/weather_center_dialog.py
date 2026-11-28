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
from datetime import UTC
from pathlib import Path
from typing import Any

from quill.core.list_follow import gone_sentence
from quill.core.weather import locations as loc_store
from quill.core.weather import nws, render, report_extras
from quill.core.weather import settings as settings_mod
from quill.core.weather.models import WeatherLocation, WeatherReport
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name
from quill.ui.dpi import dip_size
from quill.ui.spoken_name import set_spoken_name
from quill.ui.surface_lifetime import surface_tasks
from quill.ui.weather import center_follow as follow
from quill.ui.weather.center_text import (
    NO_LOCATIONS,
    _alert_detail_text,
    _alert_list_label,
    _period_detail_text,
    _temp_words,
)


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
        windows: object | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._menu_id_refs: list[object] = []
        self._data_dir = data_dir
        # Every task this window starts is tied to its lifetime (qc.md F-02).
        self._task_manager = surface_tasks(task_manager, lambda: getattr(self, "_surface", None))
        self._safe_mode = safe_mode
        self._announce = announce_cb or (lambda _m: None)
        self._store = loc_store.load_locations(data_dir)
        self._settings = settings_mod.load_settings(data_dir)
        self._report: WeatherReport | None = None
        self._shown_alerts: list[Any] = []

        # Modeless wx.Frame (menu bar + &Window menu, controls on an inner panel)
        # when standalone Radio supplies a WindowManager; modal wx.Dialog for
        # embedded QUILL. self._win is the top-level window, so the child
        # Add Location / Settings dialogs parent to it correctly.
        self._windows = windows
        self._modeless = windows is not None
        if self._modeless:
            self._win = wx.Frame(parent, title="Weather Center", style=wx.DEFAULT_FRAME_STYLE)
            self._surface = wx.Panel(self._win, style=wx.TAB_TRAVERSAL)
            self._build_surface_menu_bar()
            self._win.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
            self._win.Bind(wx.EVT_CLOSE, self._on_close)
        else:
            self._win = wx.Dialog(
                parent,
                title="Weather Center",
                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            )
            self._surface = self._win
        self.dialog = self._win  # top-level window; child dialogs parent to it
        self._win.SetMinSize(dip_size(self._win, 620, 560))
        root = wx.BoxSizer(wx.VERTICAL)

        # -- location row --
        loc_row = wx.BoxSizer(wx.HORIZONTAL)
        loc_row.Add(
            wx.StaticText(self._surface, label="&Location:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._location_choice = wx.Choice(self._surface)
        set_accessible_name(self._location_choice, "Weather location")
        self._location_choice.SetHelpText(
            "Which saved place this whole window reports on. Choosing one "
            "makes it the primary location -- the one the alert watch and "
            "Quick Weather follow -- and fetches its weather right away. "
            "Delete removes the chosen place."
        )
        loc_row.Add(self._location_choice, 1, wx.EXPAND | wx.RIGHT, 6)
        self._refresh_btn = wx.Button(self._surface, label="&Refresh")
        self._refresh_btn.SetHelpText(
            "Fetch this location's weather again right now -- alerts, "
            "conditions, and every forecast. The status line at the bottom "
            "says where the data came from and how fresh it is."
        )
        self._add_btn = wx.Button(self._surface, label="&Add Location...")
        self._add_btn.SetHelpText(
            "Open Add Weather Location: search by ZIP code, city, county, "
            "or address and save a new place. It joins the Location chooser "
            "as soon as it is added."
        )
        self._remove_btn = wx.Button(self._surface, label="Re&move Location")
        self._remove_btn.SetHelpText(
            "Delete the place chosen in the Location list, immediately and "
            "without a confirmation. Pressing Delete in the Location list "
            "does the same."
        )
        self._settings_btn = wx.Button(self._surface, label="&Settings...")
        self._settings_btn.SetHelpText(
            "Open Weather Settings: units, how much forecast to show, alert "
            "filtering, refresh cadence, and the alert sound. Saved changes "
            "re-render this window immediately."
        )
        for b in (self._refresh_btn, self._add_btn, self._remove_btn, self._settings_btn):
            loc_row.Add(b, 0, wx.RIGHT, 4)
        root.Add(loc_row, 0, wx.EXPAND | wx.ALL, 10)

        # -- active alerts --
        self._alerts_label = wx.StaticText(self._surface, label="Act&ive Alerts:")
        root.Add(self._alerts_label, 0, wx.LEFT | wx.RIGHT, 10)
        self._alerts_list = wx.ListBox(self._surface)
        set_accessible_name(self._alerts_list, "Active weather alerts")
        self._alerts_list.SetHelpText(
            "Every alert in effect for this location right now, one line "
            "each: the event, the area, and its tier. Arrowing to a row "
            "fills the read-only box below with the full official text -- "
            "headline, instructions, and timing."
        )
        root.Add(self._alerts_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        # A StaticText immediately before the field is what actually names a
        # read-only TextCtrl for a screen reader;
        # set_accessible_name alone does not stick on a read-only multiline box.
        self._alert_detail_label = wx.StaticText(
            self._surface, label="Selected aler&t (read-only):"
        )
        root.Add(self._alert_detail_label, 0, wx.LEFT | wx.RIGHT, 10)
        self._alert_detail = wx.TextCtrl(
            self._surface, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        set_accessible_name(self._alert_detail, "Selected alert, full official text")
        self._alert_detail.SetHelpText(
            "The full official text of the alert highlighted in the list "
            "above: headline, severity, area, timing, instructions, and "
            "description, exactly as issued. Read-only and copyable; it "
            "follows the list selection."
        )
        root.Add(self._alert_detail, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # -- current conditions --
        root.Add(
            wx.StaticText(self._surface, label="&Current conditions:"), 0, wx.LEFT | wx.RIGHT, 10
        )
        self._current = wx.TextCtrl(
            self._surface, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        set_accessible_name(self._current, "Current conditions")
        self._current.SetHelpText(
            "The weather right now at this location, as one readable block: "
            "temperature and sky always, plus whichever details you have "
            "turned on in Settings -- feels-like, wind, humidity, sunrise, "
            "and more. Read-only and copyable, with the observation time at "
            "the end."
        )
        self._current.SetMinSize(dip_size(self._current, -1, 150))
        root.Add(self._current, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # -- forecast --
        root.Add(wx.StaticText(self._surface, label="&Forecast:"), 0, wx.LEFT | wx.RIGHT, 10)
        self._forecast_list = wx.ListBox(self._surface)
        set_accessible_name(self._forecast_list, "Forecast periods")
        self._forecast_list.SetHelpText(
            "The official forecast, one line per period -- Today, Tonight, "
            "and so on -- with its temperature and a short summary. Arrowing "
            "to a period fills the read-only box below with its full "
            "detailed forecast. Settings chooses how many periods appear."
        )
        root.Add(self._forecast_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self._period_detail_label = wx.StaticText(
            self._surface, label="Selected &period (read-only):"
        )
        root.Add(self._period_detail_label, 0, wx.LEFT | wx.RIGHT, 10)
        self._period_detail = wx.TextCtrl(
            self._surface, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        set_accessible_name(self._period_detail, "Selected forecast period, details")
        self._period_detail.SetHelpText(
            "The full detailed forecast for the period highlighted in the "
            "list above, with abbreviations spelled out for speech. "
            "Read-only and copyable; it follows the list selection."
        )
        self._period_detail.SetMinSize(dip_size(self._period_detail, -1, 72))
        root.Add(self._period_detail, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # -- hourly forecast (NWS forecastHourly) --
        root.Add(wx.StaticText(self._surface, label="Ho&urly forecast:"), 0, wx.LEFT | wx.RIGHT, 10)
        self._hourly_list = wx.ListBox(self._surface)
        set_accessible_name(self._hourly_list, "Hourly forecast, one line per hour")
        self._hourly_list.SetHelpText(
            "Hour-by-hour forecast, one line per hour with time, "
            "temperature, sky, and wind. Settings chooses how many hours it "
            "covers, up to 48, or turns the section off."
        )
        root.Add(self._hourly_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self._hourly_detail_label = wx.StaticText(
            self._surface, label="Selected &hour (read-only):"
        )
        root.Add(self._hourly_detail_label, 0, wx.LEFT | wx.RIGHT, 10)
        self._hourly_detail = wx.TextCtrl(
            self._surface, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        set_accessible_name(self._hourly_detail, "Selected hour, full details")
        self._hourly_detail.SetHelpText(
            "The highlighted hour's line as read-only, copyable text that "
            "wraps instead of scrolling off the edge. It follows the hourly "
            "list's selection."
        )
        self._hourly_detail.SetMinSize(dip_size(self._hourly_detail, -1, 48))
        root.Add(self._hourly_detail, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # -- extended daily outlook (Open-Meteo, past the NWS 7 days) --
        root.Add(
            wx.StaticText(self._surface, label="Daily &outlook (extended):"),
            0,
            wx.LEFT | wx.RIGHT,
            10,
        )
        self._daily_list = wx.ListBox(self._surface)
        set_accessible_name(self._daily_list, "Extended daily outlook, one line per day")
        self._daily_list.SetHelpText(
            "A longer-range outlook, one summary line per day, reaching "
            "past the week the period forecast covers. Settings chooses how "
            "many days it holds, up to 16, or turns the section off."
        )
        root.Add(self._daily_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self._daily_detail_label = wx.StaticText(self._surface, label="Selected &day (read-only):")
        root.Add(self._daily_detail_label, 0, wx.LEFT | wx.RIGHT, 10)
        self._daily_detail = wx.TextCtrl(
            self._surface, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        set_accessible_name(self._daily_detail, "Selected day, full details")
        self._daily_detail.SetHelpText(
            "The highlighted day's line as read-only, copyable text that "
            "wraps instead of scrolling off the edge. It follows the daily "
            "outlook's selection."
        )
        self._daily_detail.SetMinSize(dip_size(self._daily_detail, -1, 60))
        root.Add(self._daily_detail, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # -- status + close --
        self._status = wx.TextCtrl(self._surface, style=wx.TE_READONLY)
        set_accessible_name(self._status, "Weather source and freshness status")
        set_spoken_name(self._status, "Weather source and freshness status")
        self._status.SetHelpText(
            "Where this report came from and how it is doing: the National "
            "Weather Service office and zone, the observing station, and "
            "any note about data that could not be fetched. Read-only; it "
            "updates with every refresh."
        )
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        btn_row.AddStretchSpacer()
        close_btn = wx.Button(self._surface, wx.ID_CANCEL, "Close")
        close_btn.SetHelpText(
            "Close the Weather Center. Escape does the same, and alert "
            "monitoring keeps running without it."
        )
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self._surface.SetSizer(root)
        if self._modeless:
            outer = wx.BoxSizer(wx.VERTICAL)
            outer.Add(self._surface, 1, wx.EXPAND)
            self._win.SetSizer(outer)

        self._location_choice.Bind(wx.EVT_CHOICE, lambda _e: self._on_location_chosen())
        self._location_choice.Bind(wx.EVT_KEY_DOWN, self._on_location_key)
        self._remove_btn.Bind(wx.EVT_BUTTON, lambda _e: self._remove_location())
        self._alerts_list.Bind(wx.EVT_LISTBOX, lambda _e: self._on_alert_selected())
        self._forecast_list.Bind(wx.EVT_LISTBOX, lambda _e: self._on_period_selected())
        self._hourly_list.Bind(wx.EVT_LISTBOX, lambda _e: self._on_hourly_selected())
        self._daily_list.Bind(wx.EVT_LISTBOX, lambda _e: self._on_daily_selected())
        self._refresh_btn.Bind(wx.EVT_BUTTON, lambda _e: self._refresh())
        self._add_btn.Bind(wx.EVT_BUTTON, lambda _e: self._add_location())
        self._settings_btn.Bind(wx.EVT_BUTTON, lambda _e: self._open_settings())

        # Detail boxes start hidden (and out of the tab order) until there is
        # something to show -- no stopping on a blank read-only field.
        for control in (
            self._alert_detail_label,
            self._alert_detail,
            self._period_detail_label,
            self._period_detail,
            self._hourly_detail_label,
            self._hourly_detail,
            self._daily_detail_label,
            self._daily_detail,
        ):
            control.Hide()

        self._reload_location_choice()

    # -- lifecycle --------------------------------------------------------------

    def _build_surface_menu_bar(self) -> None:
        wx = self._wx
        menu_bar = wx.MenuBar()
        surface_menu = wx.Menu()
        close_id = wx.NewIdRef()
        surface_menu.Append(close_id, "&Close\tCtrl+W")
        self._win.Bind(wx.EVT_MENU, lambda _e: self._win.Close(), id=close_id)
        menu_bar.Append(surface_menu, "&Weather")
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
        self._announce("Exited Weather Center")
        event.Skip()
        self._win.Destroy()
        if previous:
            self._windows.activate(previous)

    def show(self, *, focus_alerts: bool = False) -> None:
        if self._store.locations:
            if self._settings.refresh_on_open:
                self._refresh()
            if focus_alerts:
                self._alerts_list.SetFocus()
        else:
            self._status.SetValue(NO_LOCATIONS)  # its key, and what it needs (FUX-09)
            self._add_btn.SetFocus()  # the action itself, not a pre-show announcement
        if self._modeless:
            from quill.ui.dialog_contract import show_modeless_surface

            self._windows.register(self._win, "Weather Center")
            show_modeless_surface(self._win, "Weather Center", announce=self._announce)
            return
        self._win.CentreOnParent()
        apply_modal_ids(self._win, cancel_id=self._wx.ID_CANCEL)
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self._win, "Weather Center", announce=self._announce)
        finally:
            self._win.Destroy()

    # -- location chooser -------------------------------------------------------

    def _reload_location_choice(self) -> None:
        primary = self._store.primary()
        index = self._store.locations.index(primary) if primary is not None else -1
        follow.sync_choice(
            self._location_choice, [loc.label for loc in self._store.locations], index
        )

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
        # Only the newest fetch may fill the window: a slow answer for the
        # place chosen before must not replace this one (FUX-06).
        self._fetch_request = request = getattr(self, "_fetch_request", 0) + 1

        def _work(**_kwargs: Any) -> object:
            try:
                return report_extras.fetch_report(
                    location, self._settings, self._data_dir, safe_mode=self._safe_mode
                )
            except nws.WeatherError as exc:
                return exc

        def _landed(result: object) -> None:
            if request == self._fetch_request:
                self._render_report(location, result)

        def _ok(_op: str, result: object) -> None:
            self._wx.CallAfter(_landed, result)

        self._task_manager.submit("weather-fetch", _work, on_success=_ok, on_failure=None)

    def _render_report(
        self, location: WeatherLocation, result: object, *, fetched: bool = True
    ) -> None:
        """Show *result*. *fetched* is False for a redraw of the same report
        (after Settings), which says the summary only if what it says changed."""
        if isinstance(result, nws.WeatherError):
            self._status.SetValue(f"Could not load weather: {result}")
            self._announce(f"Could not load weather. {result}")
            return
        if not isinstance(result, WeatherReport):
            return
        self._report = result
        self._reload_location_choice()  # a resolved name may have filled in

        alerts = render.filtered_alerts(result, self._settings)
        before = {alert.id: alert for alert in getattr(self, "_shown_alerts", [])}
        place_key = (location.id, location.label)
        if place_key != getattr(self, "_shown_location", place_key):
            before = {}  # another place: its alerts did not expire, they are elsewhere
            self._follow_keys_alerts: list[str] = []
        self._shown_location = place_key
        self._shown_alerts = alerts
        rows = [(a.id, _alert_list_label(a)) for a in alerts]
        at, gone = follow.fill_list(self, "alerts", self._alerts_list, rows, "No active alerts.")
        self._alerts_label.SetLabel(
            f"Active &Alerts ({len(alerts)}):" if alerts else "Active &Alerts (none):"
        )
        follow.set_text(self._alert_detail, _alert_detail_text(alerts[at]) if alerts else "")
        # Skip an empty read-only field in the tab order (no alert -> no box).
        self._show_field(self._alert_detail_label, self._alert_detail, bool(alerts))

        place = location.label
        today = result.daily[0] if result.daily else None
        local_time = ""
        if self._settings.show_local_time and result.time_zone:
            from datetime import datetime

            now = datetime.now(UTC)
            # "Right now it is <there>, and <here> where you are. Checked just now."
            local_time = render.time_summary(now, result.time_zone, place=place)
        lead = f"{local_time} " if local_time else ""
        more = "".join(f" {line}" for line in result.extras)
        if result.current is not None:
            block = render.current_conditions_block(
                result.current, today, self._settings, result.air_quality
            )
            when = ""
            if result.current.observed_at:
                observed = render.friendly_datetime(result.current.observed_at, result.time_zone)
                when = f" Observed {observed}."
            follow.set_text(self._current, f"Weather for {place}. {lead}{block}{when}" + more)
        else:
            follow.set_text(
                self._current,
                f"Weather for {place}. {lead}Current conditions are unavailable right now.{more}",
            )

        periods = result.periods[: self._settings.forecast_period_count]
        rows = [(p.name, f"{p.name}: {_temp_words(p)}, {p.short_forecast}") for p in periods]
        at, _ = follow.fill_list(
            self, "periods", self._forecast_list, rows, "Forecast unavailable."
        )
        follow.set_text(self._period_detail, _period_detail_text(periods[at]) if periods else "")
        self._show_field(self._period_detail_label, self._period_detail, bool(periods))

        hourly = result.hourly
        rows = [(h.start or h.time, h.line) for h in hourly]
        empty = "Hourly forecast unavailable."
        at, _ = follow.fill_list(self, "hourly", self._hourly_list, rows, empty)
        follow.set_text(self._hourly_detail, hourly[at].line if hourly else "")
        self._show_field(self._hourly_detail_label, self._hourly_detail, bool(hourly))

        rows = [(str(day.date), day.line) for day in result.daily]
        empty = "Extended daily outlook unavailable."
        at, _ = follow.fill_list(self, "daily", self._daily_list, rows, empty)
        follow.set_text(self._daily_detail, result.daily[at].line if result.daily else "")
        self._show_field(self._daily_detail_label, self._daily_detail, bool(result.daily))

        self._status.SetValue(self._status_line(result))
        self._surface.Layout()

        n = len(alerts)
        summary = f"Weather for {place}. "
        summary += (
            "There are no active alerts. "
            if n == 0
            else (
                f"There {'is' if n == 1 else 'are'} {n} active "
                f"alert{'' if n == 1 else 's'}. The most urgent is a {alerts[0].event}. "
            )
        )
        if result.current is not None and result.current.temperature_f is not None:
            summary += render.current_conditions_line(result.current, self._settings) + "."
        # Said for a fetch the person asked for; a redraw says it only when
        # what it says changed. An alert the reader was on that has gone is
        # said once, with it (FUX-06).
        said = (location.id, tuple(a.id for a in alerts))
        went = gone_sentence(f"The {before[gone].event}") if gone in before else ""
        speak = ""
        if self._settings.announce_alert_count_on_open and (
            fetched or said != getattr(self, "_said_summary", None) or went
        ):
            speak = f"{summary} {went}".strip()
        elif went:
            speak = went  # the summary is off, but the reader moved: say why
        if speak and went:
            # After the screen reader has read the alert the reader landed on:
            # a focus change would cut the sentence off.
            self._wx.CallLater(400, lambda: self._announce(speak) if self else None)
        elif speak:
            self._announce(speak)
        self._said_summary = said

    def _show_field(self, label: Any, field: Any, visible: bool) -> None:
        """Show or hide a label+field pair; hidden controls leave the tab order,
        so a screen-reader user never lands on an empty read-only box."""
        label.Show(visible)
        field.Show(visible)

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
            self._period_detail.SetValue(_period_detail_text(periods[index]))

    def _on_hourly_selected(self) -> None:
        if self._report is None:
            return
        index = self._hourly_list.GetSelection()
        if 0 <= index < len(self._report.hourly):
            self._hourly_detail.SetValue(self._report.hourly[index].line)

    def _on_daily_selected(self) -> None:
        if self._report is None:
            return
        index = self._daily_list.GetSelection()
        if 0 <= index < len(self._report.daily):
            self._daily_detail.SetValue(self._report.daily[index].line)

    # -- remove a location ------------------------------------------------------

    def _on_location_key(self, event: Any) -> None:
        if event.GetKeyCode() == self._wx.WXK_DELETE:
            self._remove_location()
        else:
            event.Skip()

    def _remove_location(self) -> None:
        """Remove the chosen location (the Remove button or the Delete key)."""
        location = self._current_location()
        if location is None:
            self._announce("There is no location to remove.")
            return
        label = location.label
        self._store.remove(location.id)
        loc_store.save_locations(self._data_dir, self._store)
        self._reload_location_choice()
        if self._store.locations:
            self._announce(f"Removed {label}.")
            self._refresh()
            return
        self._report = None
        # A fetch still on its way for the place just removed must not refill.
        self._fetch_request = getattr(self, "_fetch_request", 0) + 1
        for listbox in (
            self._alerts_list,
            self._forecast_list,
            self._hourly_list,
            self._daily_list,
        ):
            listbox.Set([])
        for box in (
            self._current,
            self._alert_detail,
            self._period_detail,
            self._hourly_detail,
            self._daily_detail,
            self._status,
        ):
            box.SetValue("")
        for label_ctrl, field in (
            (self._alert_detail_label, self._alert_detail),
            (self._period_detail_label, self._period_detail),
            (self._hourly_detail_label, self._hourly_detail),
            (self._daily_detail_label, self._daily_detail),
        ):
            self._show_field(label_ctrl, field, False)
        self._surface.Layout()
        self._announce(f"Removed {label}. {NO_LOCATIONS}")

    # -- sub-dialogs ------------------------------------------------------------

    def _add_location(self) -> None:
        from quill.ui.weather.add_location_dialog import AddLocationDialog

        dlg = AddLocationDialog(
            self._win,
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
            self._win,
            settings=self._settings,
            data_dir=self._data_dir,
            announce_cb=self._announce,
        )
        if dlg.show():
            self._settings = settings_mod.load_settings(self._data_dir)
            if self._report is not None:
                location = self._current_location() or self._report.location
                self._render_report(location, self._report, fetched=False)
