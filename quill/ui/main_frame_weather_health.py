"""WeatherHealthMixin -- the alert-feed health wiring for the Weather Guardian.

Thin wx glue over ``quill.core.weather.feed_health``: record what each poll
returned, say the one thing worth saying after a round (cannot reach the
service, still cannot, recovered), keep the tray tooltip honest, and open the
Alert Feed Status window. Mixed into ``WeatherMixin`` so every host that has
the Weather menu has this too.
"""

from __future__ import annotations

import time
from typing import Any


class WeatherHealthMixin:
    frame: Any
    _wx: Any
    _safe_mode: bool

    def _announce(  # provided by host
        self, message: str, *, force: bool = False, sound: str = ""
    ) -> None: ...
    def _show_weather_toast(self, title: str, body: str) -> None: ...
    @staticmethod
    def _weather_data_dir() -> Any: ...

    # -- tracker ----------------------------------------------------------

    def _weather_feed_tracker(self) -> Any:
        tracker = getattr(self, "_weather_feed_tracker_obj", None)
        if tracker is None:
            from quill.core.weather import feed_health_store

            tracker = feed_health_store.load_tracker(
                self._weather_data_dir(), safe_mode=self._safe_mode
            )
            self._weather_feed_tracker_obj = tracker
        return tracker

    def _weather_health_record(self, location: Any, result: object, hidden: Any = ()) -> bool:
        """Record one place's poll result. Returns True when it was a success.
        A failure leaves the last known alerts and success time alone."""
        from quill.core.weather import feed_health

        tracker = self._weather_feed_tracker()
        now = time.time()
        if isinstance(result, list):
            tracker.record_success(location.id, location.label, result, now, hidden_ids=hidden)
            return True
        error = result if isinstance(result, BaseException) else feed_health.FailureKind.UNREADABLE
        tracker.record_failure(location.id, location.label, error, now)
        return False

    def _weather_health_round_end(self) -> None:
        """After every poll round: save, refresh the tooltip, speak the one notice."""
        from quill.core.weather import feed_health_store

        tracker = self._weather_feed_tracker()
        now = time.time()
        notice = tracker.end_of_round(now)
        feed_health_store.save_tracker(self._weather_data_dir(), tracker)
        self._weather_health_refresh_tooltip()
        if notice is not None:
            self._announce(notice.text, force=notice.kind != "recovered")
            self._show_weather_toast(notice.title, notice.text)

    def _weather_health_unchecked_notes(self, labels_by_id: dict[str, str]) -> dict[str, str]:
        """For the start summary: label -> 'last successful check was at ...' note."""
        tracker = self._weather_feed_tracker()
        notes: dict[str, str] = {}
        for pid, label in labels_by_id.items():
            health = tracker.places.get(pid)
            notes[label] = (
                tracker.last_check_sentence([health], time.time())
                if health is not None and health.last_success is not None
                else ""
            )
        return notes

    def _weather_health_refresh_tooltip(self) -> None:
        icon = getattr(self, "_tray_icon", None)
        if icon is None:
            return
        try:
            ids = [loc.id for loc in getattr(self, "_weather_monitor_locations", [])]
            tip = self._weather_feed_tracker().tooltip(time.time(), ids or None)
            icon.SetIcon(getattr(self, "_app_icon", None) or icon.GetIcon(), tip)
        except Exception:  # noqa: BLE001 - a tooltip must never disturb a poll
            pass

    # -- the Alert Feed Status window ----------------------------------------

    def _weather_watched_places(self) -> tuple[list[str], dict[str, str]]:
        """The saved places that are being checked now, and every place's label."""
        from quill.core.weather import place_watch

        store, muted, watches, now = self._weather_watch_setup()  # type: ignore[attr-defined]
        labels = {loc.id: loc.label for loc in store.locations}
        ids = [i for i in labels if place_watch.state_of(i, muted, watches, now).checked]
        return ids, labels

    def weather_feed_status_text(self) -> str:
        ids, labels = self._weather_watched_places()
        text = self._weather_feed_tracker().status_text(ids, labels, time.time())
        note = self._weather_not_watched_note()  # type: ignore[attr-defined]
        return f"{text}\n\n{note.strip()}" if note else text

    def weather_feed_summary(self) -> str:
        ids, _labels = self._weather_watched_places()
        return self._weather_feed_tracker().summary(time.time(), ids)

    def open_weather_feed_status(self) -> None:
        """Weather > Alert Feed Status: say the state, then show the full report."""
        from quill.ui.weather.feed_status_dialog import FeedStatusDialog

        text = self.weather_feed_status_text()
        self._announce(self.weather_feed_summary())
        FeedStatusDialog(self.frame, text=text, announce_cb=self._announce).show()
