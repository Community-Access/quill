"""WeatherMixin -- the top-level Weather menu and its command handlers.

Mirrors RadioMixin (main_frame_radio.py): thin wx wiring over the wx-free
``quill/core/weather`` package, shared verbatim by standalone Quill Radio and,
later, QUILL itself. All fetching runs off the shared task manager; nothing
here holds weather state beyond what the dialogs load from disk on open.

Host requirements (already provided by RadioAppFrame / MainFrame): ``self.frame``,
``self._wx``, ``self._safe_mode``, ``self._task_manager``, ``self._announce``,
and ``self._show_message_box``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from quill.core.radio import wxindex
from quill.core.radio.models import RadioStation
from quill.core.radio.wxindex_models import to_radio_station

_SAFE_MODE_WEATHER = (
    "Weather is a network service and is turned off in Safe Mode. "
    "Restart without Safe Mode to use it."
)


def local_noaa_radio_station(
    *, latitude: float, longitude: float, county: str = "", safe_mode: bool = False
) -> RadioStation | None:
    """Resolve the NOAA Weather Radio station nearest a location (pure, no wx).

    Delegates to ``wxindex.local_stations`` -- county/SAME match first, else
    nearest-by-coordinate over the bundled snapshot -- and adapts the first
    hit to a playable ``RadioStation`` via ``to_radio_station``. None when
    nothing resolves, so the caller can prompt instead of playing silence.
    """
    stations = wxindex.local_stations(latitude, longitude, county=county, safe_mode=safe_mode)
    return to_radio_station(stations[0]) if stations else None


class WeatherMixin:
    # Attributes provided by the host frame.
    frame: Any
    _wx: Any
    _safe_mode: bool
    _task_manager: Any

    def _announce(self, message: str, *, force: bool = False) -> None: ...  # provided by host
    def _show_message_box(self, message: str, caption: str, style: int) -> int:
        return 0

    # -- menu -------------------------------------------------------------------

    def _weather_area_enabled(self, area_id: str) -> bool:
        """Whether a switchable Weather sub-area is on for this host. Hosts that
        do not track app areas (e.g. Quill Radio) return True, so their Weather
        menu is complete; the standalone Quill Weather app can turn areas off."""
        checker = getattr(self, "_app_area_enabled", None)
        return True if checker is None else bool(checker(area_id))

    def open_weather_app(self) -> None:
        """Launch the standalone Quill Weather app in its own window/tray; if it
        isn't installed, warmly offer to download and install it."""
        from quill.ui.companion_offer import try_open_or_offer

        try_open_or_offer(self, "weather")

    def _append_weather_menu(self, menu_bar: Any) -> None:
        """Build and append the top-level &Weather menu (PRD 20 command IDs)."""
        wx = self._wx
        menu = wx.Menu()
        # Hosts that prefer to hand weather off to its own app (Quill Radio, and
        # QUILL) offer this at the very top; the Quill Weather app itself does not.
        if getattr(self, "_weather_offers_app_launch", False):
            open_app_id = wx.NewIdRef()
            menu.Append(open_app_id, "&Open the Quill Weather App")
            self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_weather_app(), id=open_app_id)
            menu.AppendSeparator()
        now_id, quick_id, alerts_id, add_id, settings_id = (wx.NewIdRef() for _ in range(5))
        noaa_listen_id, noaa_update_id = (wx.NewIdRef() for _ in range(2))
        menu.Append(now_id, "&Weather Now...\tCtrl+Shift+W")
        menu.Append(quick_id, "&Quick Weather\tCtrl+Shift+Q")
        menu.Append(alerts_id, "Active &Alerts...")
        menu.AppendSeparator()
        test_id = wx.NewIdRef()
        menu.Append(add_id, "&Add Location...")
        menu.Append(settings_id, "&Settings...")
        menu.Append(test_id, "&Test Alert (preview sound, tray, and dialog)")
        if self._weather_area_enabled("noaa_radio"):
            menu.AppendSeparator()
            menu.Append(noaa_listen_id, "&Listen to your Local NOAA Weather Radio")
            menu.Append(noaa_update_id, "&Update NOAA Weather Radio Directory")
            self.frame.Bind(
                wx.EVT_MENU, lambda _e: self.listen_local_noaa_radio(), id=noaa_listen_id
            )
            self.frame.Bind(
                wx.EVT_MENU, lambda _e: self.update_noaa_radio_directory(), id=noaa_update_id
            )

        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_weather_center(), id=now_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.weather_quick(), id=quick_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_weather_center(focus_alerts=True), id=alerts_id
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_weather_add_location(), id=add_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_weather_settings(), id=settings_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.weather_test_alert(), id=test_id)

        # Monitor state is initialized unconditionally so the app's startup path
        # (start_weather_monitoring_if_enabled) is always safe, even when the
        # Monitoring area's menu items are hidden.
        self._weather_monitor_timer: Any = None
        #: Every location currently being watched, and one MonitorState each
        #: (keyed by location id) so alerts are tracked and announced per place.
        self._weather_monitor_locations: list[Any] = []
        self._weather_monitor_states: dict[str, Any] = {}
        self._weather_monitor_config: Any = None
        self._weather_monitor_paused = False
        #: Per poll round: locations still in flight, and their baseline counts
        #: (so the combined "monitoring on for N places" line speaks once).
        self._weather_monitor_round_pending = 0
        self._weather_monitor_round_active = False
        self._weather_monitor_baseline_counts: dict[str, int] = {}
        self._weather_monitor_menu_item = None
        self._weather_monitor_pause_item = None
        if self._weather_area_enabled("monitoring"):
            menu.AppendSeparator()
            monitor_id = wx.NewIdRef()
            self._weather_monitor_menu_id = monitor_id
            self._weather_monitor_menu_item = menu.Append(
                monitor_id, self._weather_monitor_menu_text()
            )
            self.frame.Bind(wx.EVT_MENU, lambda _e: self.toggle_weather_monitoring(), id=monitor_id)
            pause_id = wx.NewIdRef()
            self._weather_monitor_pause_id = pause_id
            self._weather_monitor_pause_item = menu.Append(
                pause_id, self._weather_monitor_pause_text()
            )
            self._weather_monitor_pause_item.Enable(False)
            self.frame.Bind(
                wx.EVT_MENU, lambda _e: self.toggle_weather_monitoring_pause(), id=pause_id
            )

        menu_bar.Append(menu, "&Weather")

    # -- guards / helpers -------------------------------------------------------

    def _weather_blocked_in_safe_mode(self) -> bool:
        if self._safe_mode:
            self._show_message_box(
                _SAFE_MODE_WEATHER, "Weather", self._wx.ICON_INFORMATION | self._wx.OK
            )
            return True
        return False

    @staticmethod
    def _weather_data_dir() -> Any:
        from quill.core.paths import app_data_dir

        return app_data_dir()

    # -- commands ---------------------------------------------------------------

    def open_weather_center(self, *, focus_alerts: bool = False) -> None:
        """Open the accessible, text-only Weather Center."""
        if self._weather_blocked_in_safe_mode():
            return
        from quill.ui.weather.weather_center_dialog import WeatherCenterDialog

        WeatherCenterDialog(
            self.frame,
            data_dir=self._weather_data_dir(),
            task_manager=self._task_manager,
            safe_mode=self._safe_mode,
            announce_cb=self._announce,
            windows=getattr(self, "_windows", None),
        ).show(focus_alerts=focus_alerts)

    def open_weather_add_location(self) -> None:
        if self._weather_blocked_in_safe_mode():
            return
        from quill.core.weather import locations as loc_store
        from quill.ui.weather.add_location_dialog import AddLocationDialog

        data_dir = self._weather_data_dir()
        store = loc_store.load_locations(data_dir)
        AddLocationDialog(
            self.frame,
            store=store,
            data_dir=data_dir,
            task_manager=self._task_manager,
            safe_mode=self._safe_mode,
            announce_cb=self._announce,
        ).show()

    def open_weather_settings(self) -> None:
        from quill.core.weather import settings as settings_mod
        from quill.ui.weather.settings_dialog import WeatherSettingsDialog

        data_dir = self._weather_data_dir()
        WeatherSettingsDialog(
            self.frame,
            settings=settings_mod.load_settings(data_dir),
            data_dir=data_dir,
            announce_cb=self._announce,
        ).show()

    def weather_quick(self) -> None:
        """Speak/announce a one-line summary for the primary location, without
        opening a window (PRD 6.2). Opens Add Location if none exist yet."""
        if self._weather_blocked_in_safe_mode():
            return
        from quill.core.weather import locations as loc_store
        from quill.core.weather import nws
        from quill.core.weather import settings as settings_mod

        data_dir = self._weather_data_dir()
        store = loc_store.load_locations(data_dir)
        location = store.primary()
        if location is None:
            self._announce("No weather location yet. Opening Add Location.")
            self.open_weather_add_location()
            return
        settings = settings_mod.load_settings(data_dir)
        self._announce(f"Getting weather for {location.label}.")

        def _work(**_kwargs: Any) -> object:
            try:
                return nws.fetch_report_worldwide(
                    location,
                    safe_mode=self._safe_mode,
                    hourly_hours=0,  # Quick Weather is a one-liner; skip the hourly pull
                    temperature_unit=settings.temperature_unit,
                )
            except nws.WeatherError as exc:
                return exc

        def _ok(_op: str, result: object) -> None:
            self._wx.CallAfter(self._weather_quick_done, result, settings)

        self._task_manager.submit("weather-quick", _work, on_success=_ok, on_failure=None)

    def _weather_quick_done(self, result: object, settings: Any) -> None:
        from quill.core.weather import nws, render
        from quill.core.weather.models import WeatherReport

        if isinstance(result, nws.WeatherError):
            self._announce(f"Could not get weather. {result}")
            return
        if isinstance(result, WeatherReport):
            line = render.quick_weather_line(result, settings)
            if settings.show_local_time and result.time_zone:
                place = result.location.resolved_name or result.location.label
                local_time = render.time_summary(datetime.now(UTC), result.time_zone, place=place)
                if local_time:
                    line = f"{line} {local_time}"
            self._announce(line)

    # -- NOAA Weather Radio -------------------------------------------------

    def listen_local_noaa_radio(self) -> None:
        """Weather > Listen to your Local NOAA Weather Radio: resolve the
        nearest station for the saved (primary) location and play it through
        the shared Internet Radio controller, offering to pin it to
        Favorites. Opens Add Location when no location is saved yet."""
        if self._weather_blocked_in_safe_mode():
            return
        from quill.core.weather import locations as loc_store

        data_dir = self._weather_data_dir()
        store = loc_store.load_locations(data_dir)
        location = store.primary()
        if location is None:
            self._announce("No weather location yet. Opening Add Location.")
            self.open_weather_add_location()
            return
        self._announce(f"Finding your local NOAA Weather Radio station for {location.label}...")

        def _work(**_kwargs: Any) -> object:
            return local_noaa_radio_station(
                latitude=location.latitude,
                longitude=location.longitude,
                safe_mode=self._safe_mode,
            )

        def _ok(_op: str, result: object) -> None:
            self._wx.CallAfter(self._play_local_noaa_station, result, location.label)

        self._task_manager.submit("weather-noaa-local", _work, on_success=_ok, on_failure=None)

    def _play_local_noaa_station(self, result: object, location_label: str) -> None:
        if not isinstance(result, RadioStation):
            self._show_message_box(
                f"Could not find a NOAA Weather Radio station near {location_label}.",
                "NOAA Weather Radio",
                self._wx.OK | self._wx.ICON_INFORMATION,
            )
            return
        controller = getattr(self, "_radio_controller", None)
        if controller is None:
            # A host without the radio engine (e.g. the standalone Quill Weather
            # app) can find the station but cannot play it -- say so rather than
            # letting the menu item do nothing.
            self._show_message_box(
                f"Your nearest NOAA Weather Radio station is {result.name}. "
                "Playing it needs the radio engine, which this app does not include -- "
                "open it in Quill Radio to listen.",
                "NOAA Weather Radio",
                self._wx.OK | self._wx.ICON_INFORMATION,
            )
            return
        controller.play_station(result)
        self._announce(f"Playing {result.name}")
        favorites = getattr(self, "_radio_favorites", None)
        if favorites is None or favorites.contains(result):
            return
        answer = self._show_message_box(
            f"Add {result.name} to Favorites?",
            "NOAA Weather Radio",
            self._wx.YES_NO | self._wx.ICON_QUESTION,
        )
        if answer == self._wx.YES:
            favorites.add(result)
            save_favorites = getattr(self, "_save_radio_favorites", None)
            if save_favorites is not None:
                save_favorites()
            self._announce(f"Added {result.name} to Favorites")

    def update_noaa_radio_directory(self) -> None:
        """Weather > Update NOAA Weather Radio Directory: force a live pull of
        the whole WeatherIndex directory (states + stations) off-thread, then
        announce the refreshed counts. Errors are reported honestly rather
        than silently falling back to a stale cache (matches
        ``wxindex.refresh_directory``'s own contract)."""
        if self._weather_blocked_in_safe_mode():
            return
        self._announce("Updating the NOAA Weather Radio directory...")

        def _work(**_kwargs: Any) -> object:
            try:
                return wxindex.refresh_directory(safe_mode=self._safe_mode)
            except wxindex.WxIndexError as exc:
                return exc

        def _ok(_op: str, result: object) -> None:
            self._wx.CallAfter(self._noaa_radio_directory_updated, result)

        self._task_manager.submit(
            "weather-noaa-directory-update", _work, on_success=_ok, on_failure=None
        )

    def _noaa_radio_directory_updated(self, result: object) -> None:
        if isinstance(result, wxindex.RefreshResult):
            self._announce(
                f"NOAA Weather Radio directory updated: {result.station_count} stations, "
                f"{result.state_count} states, as of {result.generated_at}."
            )
            return
        self._announce(f"Could not update the NOAA Weather Radio directory. {result}")

    # -- Weather monitoring (Weather Guardian, US alerts) -------------------

    def _weather_monitoring_active(self) -> bool:
        return getattr(self, "_weather_monitor_timer", None) is not None

    def _weather_monitor_menu_text(self) -> str:
        """The toggle item's label, reflecting the current state. The chord
        stays on the label so the accelerator survives a relabel."""
        verb = "Stop" if self._weather_monitoring_active() else "Start"
        return f"{verb} Weather &Monitoring\tCtrl+Shift+M"

    def _weather_monitor_pause_text(self) -> str:
        paused = getattr(self, "_weather_monitor_paused", False)
        return "Resume Alert Chec&ks" if paused else "Pause Alert Chec&ks"

    def _refresh_weather_monitor_menu_item(self) -> None:
        item = getattr(self, "_weather_monitor_menu_item", None)
        if item is not None:
            item.SetItemLabel(self._weather_monitor_menu_text())
        pause_item = getattr(self, "_weather_monitor_pause_item", None)
        if pause_item is not None:
            pause_item.SetItemLabel(self._weather_monitor_pause_text())
            # Pause/Resume only makes sense while the watch is running.
            pause_item.Enable(self._weather_monitoring_active())

    def toggle_weather_monitoring_pause(self) -> None:
        """Weather > Pause/Resume Alert Checks: a temporary snooze that halts the
        poll without turning monitoring off (Stop Weather Monitoring is the full
        off). A paused watch stays enabled and resumes cleanly."""
        if not self._weather_monitoring_active():
            self._announce("Weather monitoring is not on. Choose Start Weather Monitoring first.")
            return
        if getattr(self, "_weather_monitor_paused", False):
            self._weather_monitor_paused = False
            self._refresh_weather_monitor_menu_item()
            self._announce("Resuming weather alert checks.")
            self._weather_monitor_poll()  # an immediate poll re-arms the timer
        else:
            timer = getattr(self, "_weather_monitor_timer", None)
            if timer is not None:
                try:
                    timer.Stop()
                except Exception:  # noqa: BLE001 - stopping a dead timer must not raise
                    pass
            self._weather_monitor_paused = True
            self._refresh_weather_monitor_menu_item()
            self._announce("Weather alert checks paused. Choose Resume Alert Checks to continue.")

    def toggle_weather_monitoring(self) -> None:
        """Weather > Start/Stop Weather Monitoring (also Ctrl+Shift+M)."""
        if self._weather_monitoring_active():
            self.stop_weather_monitoring()
        else:
            self.start_weather_monitoring()

    def start_weather_monitoring(self, *, announce: bool = True) -> None:
        """Begin watching one US location's active alerts on a timer, speaking
        newly issued watches/warnings/advisories as they appear. Persists the
        on state so the next launch resumes it."""
        if self._weather_blocked_in_safe_mode():
            return
        from quill.core.weather import locations as loc_store
        from quill.core.weather import monitor

        if self._weather_monitoring_active():
            return
        data_dir = self._weather_data_dir()
        config = monitor.load_config(data_dir)
        store = loc_store.load_locations(data_dir)
        primary = store.primary()
        watched_ids = config.watched_ids(fallback=primary.id if primary is not None else "")
        locations = [loc for cid in watched_ids if (loc := store.find(cid)) is not None]
        if not locations:
            # Force a choice before monitoring can start: there is nothing to watch.
            self._announce("No weather location to monitor yet. Opening Add Location.")
            self.open_weather_add_location()
            return

        self._weather_monitor_locations = locations
        self._weather_monitor_states = {loc.id: monitor.MonitorState() for loc in locations}
        self._weather_monitor_config = config
        self._weather_monitor_paused = False
        self._weather_monitor_baseline_counts = {}
        config.enabled = True
        config.location_ids = [loc.id for loc in locations]
        config.location_id = locations[0].id
        monitor.save_config(data_dir, config)

        wx = self._wx
        timer = wx.Timer(self.frame)
        self.frame.Bind(wx.EVT_TIMER, self._on_weather_monitor_timer, timer)
        self._weather_monitor_timer = timer
        # A self-rescheduling one-shot (StartOnce) rather than a fixed repeat, so
        # each poll can pick the next cadence -- normal, or the tighter
        # severe-weather interval while an alert is active. The immediate poll
        # below sets the real cadence when it returns; this is the fallback tick
        # in case that first poll's callback never fires.
        timer.StartOnce(config.poll_seconds(False) * 1000)
        self._refresh_weather_monitor_menu_item()
        if announce:
            # Instant feedback; the baseline polls speak the full situation
            # (how many alerts are active, per place) a moment later.
            if len(locations) == 1:
                where = locations[0].label
            else:
                labels = [loc.label for loc in locations]
                where = f"{len(labels)} places: " + monitor._join_places(labels)
            self._announce(f"Turning on weather monitoring for {where}.")
        self._weather_monitor_poll()  # an immediate baseline poll

    def stop_weather_monitoring(self, *, announce: bool = True, persist: bool = True) -> None:
        """Stop the alert watch. ``persist`` writes the off state (a user turning
        it off); the app's shutdown passes ``persist=False`` so a clean exit
        leaves it on to resume next launch."""
        from quill.core.weather import monitor

        timer = getattr(self, "_weather_monitor_timer", None)
        if timer is not None:
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001 - stopping a dead timer must not raise
                pass
        was_active = timer is not None
        self._weather_monitor_timer = None
        self._weather_monitor_states = {}
        self._weather_monitor_config = None
        self._weather_monitor_paused = False
        locations = getattr(self, "_weather_monitor_locations", [])
        self._weather_monitor_locations = []
        if persist:
            try:
                data_dir = self._weather_data_dir()
                config = monitor.load_config(data_dir)
                config.enabled = False
                monitor.save_config(data_dir, config)
            except Exception:  # noqa: BLE001 - persistence is best-effort on stop
                pass
        self._refresh_weather_monitor_menu_item()
        if announce and was_active:
            if len(locations) == 1:
                where = f" for {locations[0].label}"
            elif locations:
                where = f" for {len(locations)} places"
            else:
                where = ""
            self._announce(f"Weather monitoring off{where}.")

    def start_weather_monitoring_if_enabled(self) -> None:
        """Resume monitoring on launch when it was left on (host calls this
        once the frame and task manager are ready)."""
        from quill.core.weather import monitor

        try:
            config = monitor.load_config(self._weather_data_dir())
        except Exception:  # noqa: BLE001
            return
        if config.enabled and not self._safe_mode:
            self.start_weather_monitoring(announce=False)

    def _on_weather_monitor_timer(self, _event: object) -> None:
        self._weather_monitor_poll()

    def _schedule_next_monitor_poll(self, has_active_alerts: bool) -> None:
        """Arm the one-shot timer for the next poll, tightening the cadence when
        an alert is active (severe-weather mode)."""
        timer = getattr(self, "_weather_monitor_timer", None)
        config = getattr(self, "_weather_monitor_config", None)
        if timer is None or config is None:
            return  # monitoring was stopped
        timer.StartOnce(max(1, config.poll_seconds(has_active_alerts)) * 1000)

    def _weather_monitor_poll(self) -> None:
        locations = getattr(self, "_weather_monitor_locations", [])
        if not locations or getattr(self, "_weather_monitor_paused", False):
            return
        from quill.core.weather import nws

        # One round = one fetch per watched location. The round-pending counter
        # lets the last poll to return arm the next tick exactly once (so N
        # locations never spawn N overlapping timers).
        self._weather_monitor_round_pending = len(locations)
        self._weather_monitor_round_active = False

        def _make_work(loc: Any) -> Any:
            def _work(**_kwargs: Any) -> object:
                try:
                    return nws.active_alerts(loc.latitude, loc.longitude, safe_mode=self._safe_mode)
                except nws.WeatherError as exc:
                    return exc

            return _work

        for location in locations:
            loc = location

            def _ok(_op: str, result: object, loc: Any = loc) -> None:
                self._wx.CallAfter(self._weather_monitor_poll_done, loc, result)

            self._task_manager.submit(
                "weather-monitor", _make_work(loc), on_success=_ok, on_failure=None
            )

    def _weather_monitor_poll_done(self, location: Any, result: object) -> None:
        from quill.core.weather import monitor

        states = getattr(self, "_weather_monitor_states", {})
        state = states.get(getattr(location, "id", None))
        if state is None:
            return  # monitoring was stopped/reconfigured while the poll was in flight
        if getattr(self, "_weather_monitor_paused", False):
            return  # paused mid-flight: stay quiet, do not re-arm
        try:
            if not isinstance(result, list):
                return  # a transient fetch error (e.g. offline); try again next tick
            update = monitor.apply_poll(state, result)
            # Persist the union of every watched place's seen ids, so the
            # OS-scheduled background check never re-toasts an alert this window
            # already spoke (alert ids are globally unique across locations).
            seen: set[str] = set()
            for st in states.values():
                seen |= st.known_alert_ids
            monitor.save_notified_ids(self._weather_data_dir(), seen)
            if result:
                self._weather_monitor_round_active = True
            if update.is_baseline:
                # Collect each place's baseline count; the combined "monitoring on
                # for N places" line is spoken once, when the last baseline lands.
                self._weather_monitor_baseline_counts[location.label] = len(result)
            else:
                if update.new_alerts:
                    self._play_weather_alert_sound()
                    top = update.new_alerts[0]
                    self._show_weather_toast(
                        f"Weather alert: {top.event}",
                        top.headline or f"A {top.event} is in effect for {location.label}.",
                    )
                message = monitor.update_announcement(update, location.label)
                if message:
                    self._announce(message, force=monitor.should_force_speech(update))
        finally:
            self._weather_monitor_round_pending -= 1
            if self._weather_monitor_round_pending <= 0:
                self._finish_weather_monitor_round()

    def _finish_weather_monitor_round(self) -> None:
        """Called once per poll round after every location has returned: speak the
        one-time combined baseline summary (if this was the start round) and arm
        the next tick with a single timer."""
        from quill.core.weather import monitor

        config = getattr(self, "_weather_monitor_config", None)
        counts = self._weather_monitor_baseline_counts
        if counts and config is not None:
            # Every place baselined this round -> the start round. Speak it once.
            self._announce(monitor.start_summary_multi(dict(counts), config))
            self._weather_monitor_baseline_counts = {}
        self._schedule_next_monitor_poll(self._weather_monitor_round_active)

    # -- test alert (preview the whole experience) --------------------------

    def weather_test_alert(self) -> None:
        """Weather > Test Alert: let the user preview exactly what a real alert
        does -- the spoken/shown text, the sound, a system-tray toast, and the
        alert dialog -- all clearly marked as a TEST and dismissable. Does not
        touch the network or the monitor's real state."""
        headline = "This is a TEST of Quill Weather alerts. No action is needed."
        # 1) The sound cue (honoring the user's enable + custom-file choice, so
        #    the test reflects what they have actually configured).
        self._play_weather_alert_sound()
        # 2) Spoken, forced so it interrupts like a real urgent alert would.
        self._announce(f"Test weather alert. {headline}", force=True)
        # 3) A system-tray toast, marked as a test.
        self._show_weather_toast(
            "[TEST] Weather alert", "This is a test of Quill Weather alerts. No action is needed."
        )
        # 4) The alert dialog, dismissable.
        body = (
            "TEST WEATHER ALERT\n\n"
            f"{headline}\n\n"
            "Severity Severe, urgency Expected, certainty Observed. (Sample values.)\n"
            "Area: your area (test).\n\n"
            "Instructions: This is only a test. When a real alert is issued, its official "
            "instructions appear here -- follow them.\n\n"
            "This preview shows how a real National Weather Service alert would be announced, "
            "sounded, shown in the system tray, and displayed. Select OK to dismiss it."
        )
        self._show_message_box(body, "Test Weather Alert", self._wx.OK | self._wx.ICON_INFORMATION)

    def _show_weather_toast(self, title: str, body: str) -> None:
        """Show a Windows notification-area toast (screen readers announce it).
        Best-effort; a toast failure never disrupts the rest of the alert."""
        try:
            import wx.adv

            note = wx.adv.NotificationMessage(title, body, self.frame)
            try:
                note.SetFlags(self._wx.ICON_WARNING)
            except Exception:  # noqa: BLE001 - flags are cosmetic
                pass
            note.Show(timeout=wx.adv.NotificationMessage.Timeout_Auto)
        except Exception:  # noqa: BLE001 - a toast must never crash the caller
            pass

    def _play_weather_alert_sound(self) -> None:
        """Play the alert cue for a newly-issued alert, honoring the user's
        enable toggle and custom-sound choice. Best-effort; never raises."""
        from quill.core.weather import settings as settings_mod

        try:
            settings = settings_mod.load_settings(self._weather_data_dir())
            if not settings.alert_sound_enabled:
                return
            from quill.platform import alert_sound

            alert_sound.play_alert_sound(settings.alert_sound_path, settings.alert_sound_repeat)
        except Exception:  # noqa: BLE001 - a sound must never disrupt the alert
            pass
