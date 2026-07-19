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

_SAFE_MODE_WEATHER = (
    "Weather is a network service and is turned off in Safe Mode. "
    "Restart without Safe Mode to use it."
)


class WeatherMixin:
    # Attributes provided by the host frame.
    frame: Any
    _wx: Any
    _safe_mode: bool
    _task_manager: Any

    def _announce(self, message: str) -> None: ...  # provided by host
    def _show_message_box(self, message: str, caption: str, style: int) -> None: ...

    # -- menu -------------------------------------------------------------------

    def _append_weather_menu(self, menu_bar: Any) -> None:
        """Build and append the top-level &Weather menu (PRD 20 command IDs)."""
        wx = self._wx
        menu = wx.Menu()
        now_id, quick_id, alerts_id, add_id, settings_id = (wx.NewIdRef() for _ in range(5))
        menu.Append(now_id, "&Weather Now...\tCtrl+Shift+W")
        menu.Append(quick_id, "&Quick Weather\tCtrl+Shift+Q")
        menu.Append(alerts_id, "Active &Alerts...")
        menu.AppendSeparator()
        menu.Append(add_id, "&Add Location...")
        menu.Append(settings_id, "&Settings...")

        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_weather_center(), id=now_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.weather_quick(), id=quick_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_weather_center(focus_alerts=True), id=alerts_id
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_weather_add_location(), id=add_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_weather_settings(), id=settings_id)
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
                return nws.fetch_report(location, safe_mode=self._safe_mode)
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
