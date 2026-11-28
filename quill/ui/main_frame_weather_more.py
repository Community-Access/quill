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

    # -- menu ----------------------------------------------------------------------

    def _append_weather_more_items(self, menu: Any) -> None:
        wx = self._wx
        handlers = {
            "weather.past_date": self.open_weather_past_date,
            "weather.history": self.open_weather_history,
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
