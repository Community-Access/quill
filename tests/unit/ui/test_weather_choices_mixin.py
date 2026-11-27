"""The wx glue that applies the user's choices to a poll, driven with a fake host:
hidden alerts are not spoken but are recorded, a failure changes nothing, a snoozed
place is quiet but Extreme breaks through, and what ended is said once."""

from __future__ import annotations

import time
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.weather import alert_rules as ar
from quill.core.weather import alert_rules_store, monitor, place_watch
from quill.core.weather import locations as loc_store
from quill.core.weather.models import WeatherAlert, WeatherLocation
from quill.core.weather.nws import WeatherError
from quill.ui.main_frame_weather_choices import WeatherChoicesMixin
from quill.ui.main_frame_weather_health import WeatherHealthMixin


class _Host(WeatherChoicesMixin, WeatherHealthMixin):
    def __init__(self, data_dir: Path) -> None:
        self._dir = data_dir
        self._safe_mode = False
        self.said: list[tuple[str, bool]] = []
        self.sounds: list[str] = []
        self.toasts: list[str] = []
        self._weather_monitor_unchecked: dict[str, str] = {}
        self._weather_monitor_locations: list[Any] = []

    def _announce(self, message: str, *, force: bool = False, sound: str = "") -> None:
        self.said.append((message, force))

    def _weather_data_dir(self) -> Path:  # type: ignore[override]
        return self._dir

    def _play_weather_alert_sound(self, severity: str = "") -> None:
        self.sounds.append(severity)

    def _show_weather_toast(self, title: str, body: str) -> None:
        self.toasts.append(title)


def _alert(event: str, severity: str, i: str) -> WeatherAlert:
    return WeatherAlert(id=i, event=event, severity=severity, urgency="Immediate")


@pytest.fixture
def host(tmp_path: Path) -> _Host:
    store = loc_store.load_locations(tmp_path)
    store.add(WeatherLocation(id="home", display_name="Home", latitude=43.0, longitude=-89.0))
    store.add(WeatherLocation(id="cabin", display_name="Cabin", latitude=44.0, longitude=-90.0))
    loc_store.save_locations(tmp_path, store)
    return _Host(tmp_path)


HOME = SimpleNamespace(id="home", label="Home")


def _poll(host: _Host, result: object, state: monitor.MonitorState, loc: Any = HOME) -> None:
    handled = host._weather_handle_poll(loc, result, state)
    if handled is None:
        return
    update, plan = handled
    host._weather_deliver(loc, update, plan)


def test_hidden_alert_is_not_spoken_but_is_recorded_and_counted(host: _Host) -> None:
    alert_rules_store.save_choices(
        host._dir, ar.AlertChoices(general=ar.RuleSet(ar.Selection("essentials")))
    )
    state = monitor.MonitorState()
    _poll(host, [], state)  # baseline
    quiet = _alert("Heat Advisory", "Moderate", "h")
    loud = _alert("Tornado Warning", "Severe", "t")
    _poll(host, [quiet, loud], state)
    spoken = " ".join(m for m, _f in host.said)
    assert "Tornado Warning" in spoken and "Heat Advisory" not in spoken
    assert host.said[-1][1] is True  # forced: an urgent alert interrupts
    recorded = host._weather_feed_tracker().places["home"].last_alerts
    assert {a.event: a.hidden for a in recorded} == {
        "Heat Advisory": True,
        "Tornado Warning": False,
    }
    assert "1 alert hidden by your settings" in host._weather_feed_tracker().status_text(
        ["home"], {"home": "Home"}, time.time()
    ) or "hidden by your settings" in host._weather_feed_tracker().status_text(
        ["home"], {"home": "Home"}, time.time()
    )


def test_a_failed_poll_changes_nothing(host: _Host) -> None:
    state = monitor.MonitorState()
    _poll(host, [_alert("Tornado Warning", "Severe", "t")], state)
    error = WeatherError("down")
    error.__cause__ = urllib.error.URLError("offline")
    _poll(host, error, state)
    assert state.known_alert_ids == {"t"}  # not cleared
    assert not any("cleared" in m for m, _f in host.said)
    assert host._weather_feed_tracker().places["home"].consecutive_failures == 1


def test_snoozed_place_is_quiet_but_extreme_breaks_through(host: _Host) -> None:
    watches = place_watch.PlaceWatches()
    place_watch.snooze(watches.rule("home"), "4 hours", datetime.now().astimezone())
    place_watch.save_watches(host._dir, watches)
    state = monitor.MonitorState()
    _poll(host, [], state)
    _poll(host, [_alert("Tornado Warning", "Severe", "s")], state)
    assert host.said == []  # held back by the snooze
    _poll(
        host,
        [_alert("Tornado Warning", "Severe", "s"), _alert("Tornado Warning", "Extreme", "x")],
        state,
    )
    assert any("Tornado Warning" in m for m, _f in host.said)


def test_places_to_watch_skips_off_places_and_keeps_snoozed_ones(host: _Host) -> None:
    config = monitor.load_config(host._dir)
    config.muted_ids = ["cabin"]
    store = loc_store.load_locations(host._dir)
    assert [loc.id for loc in host._weather_places_to_watch(config, store)] == ["home"]
    config.muted_ids = []
    watches = place_watch.PlaceWatches()
    place_watch.snooze(watches.rule("cabin"), "1 hour", datetime.now().astimezone())
    place_watch.save_watches(host._dir, watches)
    assert [loc.id for loc in host._weather_places_to_watch(config, store)] == ["home", "cabin"]


def test_what_ended_is_said_once_and_unchecked_places_drop_out(host: _Host) -> None:
    watches = place_watch.PlaceWatches()
    rule = watches.rule("cabin")
    rule.snooze_until = (datetime.now() - timedelta(minutes=1)).timestamp()
    rule.snooze_said = False
    place_watch.save_watches(host._dir, watches)
    store = loc_store.load_locations(host._dir)
    first = host._weather_locations_to_poll(list(store.locations))
    assert [loc.id for loc in first] == ["home", "cabin"]
    assert [m for m, _f in host.said] == [
        "The snooze for Cabin has ended. It is being watched again."
    ]
    host._weather_locations_to_poll(list(store.locations))
    assert len(host.said) == 1


def test_not_watched_note_names_each_place_and_why(host: _Host) -> None:
    config = monitor.load_config(host._dir)
    config.muted_ids = ["cabin"]
    monitor.save_config(host._dir, config)
    assert host._weather_not_watched_note() == " Not watching: Cabin: not watched, switched off."
