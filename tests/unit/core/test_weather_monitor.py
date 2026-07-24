"""Weather Guardian monitoring logic: baseline/diff, forced speech, spoken
announcements, and config persistence. Pure -- no wx, no network, no timer."""

from __future__ import annotations

from quill.core.weather import monitor
from quill.core.weather.models import WeatherAlert


def _alert(
    alert_id: str, event: str, severity: str = "Severe", urgency: str = "Expected", area: str = ""
) -> WeatherAlert:
    return WeatherAlert(
        id=alert_id,
        event=event,
        severity=severity,
        urgency=urgency,
        headline=f"{event} in effect",
        area_description=area,
    )


# -- diff / baseline ----------------------------------------------------------


def test_first_poll_is_a_silent_baseline() -> None:
    state = monitor.MonitorState()
    update = monitor.apply_poll(state, [_alert("a", "Heat Advisory", "Moderate")])
    assert update.is_baseline is True
    assert update.new_alerts == []
    assert state.primed is True
    assert state.known_alert_ids == {"a"}


def test_newly_issued_alert_is_flagged_after_baseline() -> None:
    state = monitor.MonitorState()
    monitor.apply_poll(state, [])  # baseline: nothing active
    update = monitor.apply_poll(state, [_alert("t1", "Tornado Warning", "Extreme", "Immediate")])
    assert [a.event for a in update.new_alerts] == ["Tornado Warning"]
    assert update.all_cleared is False


def test_unchanged_alerts_are_not_re_announced() -> None:
    state = monitor.MonitorState()
    monitor.apply_poll(state, [_alert("a", "Flood Watch")])
    update = monitor.apply_poll(state, [_alert("a", "Flood Watch")])
    assert update.new_alerts == []


def test_all_cleared_detected() -> None:
    state = monitor.MonitorState()
    monitor.apply_poll(state, [_alert("a", "Flood Watch")])
    update = monitor.apply_poll(state, [])
    assert update.all_cleared is True


def test_new_alerts_sorted_most_severe_first() -> None:
    state = monitor.MonitorState()
    monitor.apply_poll(state, [])
    update = monitor.apply_poll(
        state,
        [
            _alert("a", "Heat Advisory", "Moderate", "Expected"),
            _alert("b", "Tornado Warning", "Extreme", "Immediate"),
        ],
    )
    assert [a.event for a in update.new_alerts] == ["Tornado Warning", "Heat Advisory"]


# -- forcing speech -----------------------------------------------------------


def test_force_speech_for_urgent_and_above() -> None:
    state = monitor.MonitorState()
    monitor.apply_poll(state, [])
    warning = monitor.apply_poll(state, [_alert("t", "Tornado Warning", "Extreme", "Immediate")])
    assert monitor.should_force_speech(warning) is True


def test_no_force_speech_for_low_tier() -> None:
    state = monitor.MonitorState()
    monitor.apply_poll(state, [])
    advisory = monitor.apply_poll(state, [_alert("h", "Heat Advisory", "Moderate", "Expected")])
    assert monitor.should_force_speech(advisory) is False


# -- announcements ------------------------------------------------------------


def test_start_summary_quiet_and_busy() -> None:
    cfg = monitor.MonitorConfig(interval_minutes=10)
    assert "No active alerts" in monitor.start_summary("Tucson, AZ", [], cfg)
    busy = monitor.start_summary("Tucson, AZ", [_alert("a", "Flood Watch")], cfg)
    assert "1 active alert" in busy and "Flood Watch" in busy
    # The cadence phrase advertises severe-weather mode.
    assert "while an alert is active" in busy


def test_update_announcement_single_new_alert() -> None:
    state = monitor.MonitorState()
    monitor.apply_poll(state, [])
    update = monitor.apply_poll(state, [_alert("t", "Tornado Warning", area="Pima; Pinal")])
    msg = monitor.update_announcement(update, "Tucson, AZ")
    assert msg is not None
    assert "New weather alert for Tucson, AZ: Tornado Warning" in msg
    assert "Pima" in msg  # first area segment included


def test_update_announcement_all_clear_and_baseline() -> None:
    state = monitor.MonitorState()
    baseline = monitor.apply_poll(state, [_alert("a", "Flood Watch")])
    assert monitor.update_announcement(baseline, "X") is None  # baseline is silent
    cleared = monitor.apply_poll(state, [])
    assert "have cleared" in (monitor.update_announcement(cleared, "X") or "")


# -- config persistence -------------------------------------------------------


def test_config_round_trip(tmp_path) -> None:
    cfg = monitor.MonitorConfig(enabled=True, location_id="loc_2", interval_minutes=20)
    monitor.save_config(tmp_path, cfg)
    loaded = monitor.load_config(tmp_path)
    assert loaded.enabled is True
    assert loaded.location_id == "loc_2"
    assert loaded.interval_minutes == 20


def test_config_interval_clamped() -> None:
    assert monitor.MonitorConfig(interval_minutes=1).normalized().interval_minutes == (
        monitor.MONITOR_MIN_MINUTES
    )
    assert monitor.MonitorConfig(interval_minutes=9999).normalized().interval_minutes == (
        monitor.MONITOR_MAX_MINUTES
    )


def test_missing_config_reads_as_disabled(tmp_path) -> None:
    cfg = monitor.load_config(tmp_path)
    assert cfg.enabled is False


# -- severe-weather fast poll -------------------------------------------------


def test_poll_seconds_tightens_when_alert_active() -> None:
    cfg = monitor.MonitorConfig(interval_minutes=10, fast_interval_seconds=60).normalized()
    assert cfg.poll_seconds(has_active_alerts=False) == 600  # normal: 10 min
    assert cfg.poll_seconds(has_active_alerts=True) == 60  # severe-weather mode


def test_poll_seconds_ignores_fast_when_disabled() -> None:
    cfg = monitor.MonitorConfig(interval_minutes=10, fast_when_active=False).normalized()
    assert cfg.poll_seconds(has_active_alerts=True) == 600  # stays at normal


def test_fast_interval_floored_at_nws_courtesy_limit() -> None:
    cfg = monitor.MonitorConfig(fast_interval_seconds=5).normalized()
    assert cfg.fast_interval_seconds == monitor.MONITOR_FAST_FLOOR_SECONDS  # 30s floor


def test_fast_interval_never_exceeds_normal() -> None:
    # A "fast" poll slower than the normal cadence is meaningless: clamp it down.
    cfg = monitor.MonitorConfig(interval_minutes=5, fast_interval_seconds=9999).normalized()
    assert cfg.fast_interval_seconds == 5 * 60


def test_fast_poll_config_round_trip(tmp_path) -> None:
    cfg = monitor.MonitorConfig(
        enabled=True, interval_minutes=15, fast_when_active=True, fast_interval_seconds=45
    )
    monitor.save_config(tmp_path, cfg)
    loaded = monitor.load_config(tmp_path)
    assert loaded.fast_when_active is True
    assert loaded.fast_interval_seconds == 45


def test_cadence_phrase_reflects_mode() -> None:
    on = monitor.MonitorConfig(interval_minutes=10, fast_interval_seconds=60).normalized()
    assert "while an alert is active" in on.cadence_phrase()
    off = monitor.MonitorConfig(interval_minutes=10, fast_when_active=False).normalized()
    assert "while an alert is active" not in off.cadence_phrase()


# -- multi-location watch ------------------------------------------------------


def test_watched_ids_prefers_list_then_legacy_then_fallback() -> None:
    assert monitor.MonitorConfig(location_ids=["a", "b"]).watched_ids() == ["a", "b"]
    assert monitor.MonitorConfig(location_id="solo").watched_ids() == ["solo"]
    assert monitor.MonitorConfig().watched_ids(fallback="primary") == ["primary"]
    assert monitor.MonitorConfig().watched_ids() == []


def test_watched_ids_dedupes_order_preserving() -> None:
    cfg = monitor.MonitorConfig(location_ids=["a", "b", "a"], location_id="b")
    assert cfg.watched_ids(fallback="a") == ["a", "b"]


def test_location_ids_round_trip_and_normalize(tmp_path) -> None:
    cfg = monitor.MonitorConfig(enabled=True, location_ids=["home", "work", "home", ""])
    monitor.save_config(tmp_path, cfg)  # normalizes on save
    loaded = monitor.load_config(tmp_path)
    assert loaded.location_ids == ["home", "work"]
    assert loaded.location_id == "home"  # legacy field kept in sync


def test_legacy_single_location_migrates_to_list(tmp_path) -> None:
    from quill.core.storage import write_json_atomic

    # A pre-multi-location file: only the old single field.
    write_json_atomic(
        tmp_path / "weather_monitor.json",
        {"enabled": True, "location_id": "oldtown", "interval_minutes": 10},
    )
    loaded = monitor.load_config(tmp_path)
    assert loaded.location_ids == ["oldtown"]


def test_start_summary_multi_names_places_and_alerting() -> None:
    cfg = monitor.MonitorConfig(interval_minutes=10, fast_interval_seconds=60).normalized()
    all_clear = monitor.start_summary_multi({"Tucson": 0, "Boston": 0, "Reno": 0}, cfg)
    assert "3 places" in all_clear and "All clear" in all_clear
    assert "Tucson, Boston, and Reno" in all_clear

    some = monitor.start_summary_multi({"Tucson": 0, "Boston": 2}, cfg)
    assert "2 active alerts" in some and "Boston" in some


def test_start_summary_multi_single_place_reads_naturally() -> None:
    cfg = monitor.MonitorConfig().normalized()
    one = monitor.start_summary_multi({"Tucson": 0}, cfg)
    assert one.startswith("Weather monitoring on for Tucson.")
    assert "places" not in one


def test_start_summary_multi_no_locations_is_gentle() -> None:
    cfg = monitor.MonitorConfig().normalized()
    assert "no locations are set" in monitor.start_summary_multi({}, cfg)
