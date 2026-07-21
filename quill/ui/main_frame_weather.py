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

    def _announce(self, message: str) -> None: ...  # provided by host
    def _show_message_box(self, message: str, caption: str, style: int) -> int:
        return 0

    # -- menu -------------------------------------------------------------------

    def _append_weather_menu(self, menu_bar: Any) -> None:
        """Build and append the top-level &Weather menu (PRD 20 command IDs)."""
        wx = self._wx
        menu = wx.Menu()
        now_id, quick_id, alerts_id, add_id, settings_id = (wx.NewIdRef() for _ in range(5))
        noaa_listen_id, noaa_update_id = (wx.NewIdRef() for _ in range(2))
        menu.Append(now_id, "&Weather Now...\tCtrl+Shift+W")
        menu.Append(quick_id, "&Quick Weather\tCtrl+Shift+Q")
        menu.Append(alerts_id, "Active &Alerts...")
        menu.AppendSeparator()
        menu.Append(add_id, "&Add Location...")
        menu.Append(settings_id, "&Settings...")
        menu.AppendSeparator()
        menu.Append(noaa_listen_id, "&Listen to your Local NOAA Weather Radio")
        menu.Append(noaa_update_id, "&Update NOAA Weather Radio Directory")

        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_weather_center(), id=now_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.weather_quick(), id=quick_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_weather_center(focus_alerts=True), id=alerts_id
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_weather_add_location(), id=add_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_weather_settings(), id=settings_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.listen_local_noaa_radio(), id=noaa_listen_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.update_noaa_radio_directory(), id=noaa_update_id
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
            self._announce(render.quick_weather_line(result, settings))

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
