"""WeatherMoreMixin -- Weather on a Past Date and Weather History, on every
host that has the Weather menu.

Thin wx glue over wx-free modules: ``past_day_service`` (one past day),
``history_service`` (Weather History) and ``data_feed_health`` (one shared
record of whether each data feed could be reached). Mixed into
``WeatherMixin``.
"""

from __future__ import annotations

import time
from typing import Any

#: (command id, menu label) for the rows this mixin adds to the Weather menu.
MENU_ROWS = (
    ("weather.past_date", "Weather &on a Past Date...\tCtrl+Alt+D"),
    ("weather.history", "Weather Histor&y...\tCtrl+Shift+T"),
    ("weather.next_hours", "Ne&xt Few Hours\tCtrl+Shift+U"),
)


class WeatherMoreMixin:
    frame: Any
    _wx: Any
    _safe_mode: bool
    _task_manager: Any

    def _announce(  # provided by host
        self, message: str, *, force: bool = False, sound: str = ""
    ) -> None: ...
    @staticmethod
    def _weather_data_dir() -> Any: ...
    def _weather_blocked_in_safe_mode(self) -> bool: ...
    def open_weather_add_location(self) -> None: ...

    # -- menu ----------------------------------------------------------------------

    def _append_weather_more_items(self, menu: Any) -> None:
        wx = self._wx
        handlers = {
            "weather.past_date": self.open_weather_past_date,
            "weather.history": self.open_weather_history,
            "weather.next_hours": self.weather_next_hours,
        }
        menu.AppendSeparator()
        for command_id, label in MENU_ROWS:
            item_id = wx.NewIdRef()
            menu.Append(item_id, label)
            handler = handlers[command_id]
            self.frame.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=item_id)

    # -- shared state --------------------------------------------------------------

    def _weather_data_health(self) -> Any:
        """The one data-feed health record for this process, loaded once."""
        from quill.core.weather import data_feed_health

        return data_feed_health.shared(self._weather_data_dir(), safe_mode=self._safe_mode)

    def _weather_data_health_save(self) -> None:
        from quill.core.weather import data_feed_health

        data_feed_health.save(self._weather_data_dir(), self._weather_data_health())

    def weather_data_feed_lines(self) -> list[str]:
        """The "Data feeds" section for Alert Feed Status."""
        return list(self._weather_data_health().status_lines(time.time()))

    def _weather_primary_place(self) -> tuple[Any, Any] | None:
        """(location, settings) for the primary place, or None after offering Add."""
        from quill.core.weather import locations as loc_store
        from quill.core.weather import settings as settings_mod

        data_dir = self._weather_data_dir()
        location = loc_store.load_locations(data_dir).primary()
        if location is None:
            self._announce("No weather location yet. Opening Add Location.")
            self.open_weather_add_location()
            return None
        return location, settings_mod.load_settings(data_dir)

    def _weather_in_background(self, name: str, work: Any, done: Any) -> None:
        # Delivered on the UI thread already; a failure is handed to the same
        # callback, so an unexpected error is spoken rather than lost.
        self._task_manager.submit(
            name,
            work,
            on_success=lambda _op, result: done(result),
            on_failure=lambda _op, exc: done(exc),
        )

    # -- Next Few Hours ------------------------------------------------------------

    def weather_next_hours(self) -> None:
        """Speak the four-hour glance ahead and the daylight change."""
        if self._weather_blocked_in_safe_mode():
            return
        place = self._weather_primary_place()
        if place is None:
            return
        location, settings = place
        self._announce(f"Getting the next few hours for {location.label}.")
        health = self._weather_data_health()

        def _work(**_kwargs: Any) -> object:
            from quill.core.weather import report_extras

            return report_extras.gather(location, settings, health=health, nowcast_only=True)

        self._weather_in_background("weather-next-hours", _work, self._weather_next_hours_done)

    def _weather_next_hours_done(self, result: object) -> None:
        from quill.core.weather import data_feed_health

        self._weather_data_health_save()
        if isinstance(result, BaseException):
            self._announce(data_feed_health.failure_sentence("open_meteo_nowcast", result))
            return
        lines = result.lines() if hasattr(result, "lines") else []
        self._announce(" ".join(lines) or "Nothing is known about the next few hours.")

    # -- Weather History -----------------------------------------------------------

    def open_weather_history(self) -> None:
        if self._weather_blocked_in_safe_mode():
            return
        from quill.ui.weather.history_dialog import WeatherHistoryDialog

        WeatherHistoryDialog(
            self.frame,
            data_dir=self._weather_data_dir(),
            task_manager=self._task_manager,
            safe_mode=self._safe_mode,
            announce_cb=self._announce,
            health=self._weather_data_health(),
            on_health_changed=self._weather_data_health_save,
            open_day=lambda place_id, day: self.open_weather_past_date(
                place_id=place_id, start=day
            ),
        ).show()

    def open_weather_past_date(self, *, place_id: str = "", start: Any = None) -> None:
        """Weather on a Past Date: type a date, then move a day, week, month or year."""
        if self._weather_blocked_in_safe_mode():
            return
        from quill.ui.weather.past_date_dialog import PastDateDialog

        PastDateDialog(
            self.frame,
            data_dir=self._weather_data_dir(),
            task_manager=self._task_manager,
            safe_mode=self._safe_mode,
            announce_cb=self._announce,
            health=self._weather_data_health(),
            on_health_changed=self._weather_data_health_save,
            place_id=place_id,
            start=start,
        ).show()
