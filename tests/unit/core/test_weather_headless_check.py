"""Headless one-shot alert check (the OS-scheduled background watch): first-run
baseline, cross-process de-dup via the persisted notified-id set, skip
conditions, and toast composition. Pure -- the NWS fetch is injected."""

from __future__ import annotations

from quill.core.weather import headless_check, monitor
from quill.core.weather import locations as loc_store
from quill.core.weather.models import WeatherAlert, WeatherLocation


def _seed_location(data_dir) -> None:
    store = loc_store.WeatherLocationStore()
    store.add(WeatherLocation(display_name="Tucson, AZ", latitude=32.22, longitude=-110.97))
    loc_store.save_locations(data_dir, store)


def _alert(alert_id: str, event: str, severity: str = "Severe") -> WeatherAlert:
    return WeatherAlert(
        id=alert_id,
        event=event,
        severity=severity,
        urgency="Expected",
        headline=f"{event} in effect",
    )


def test_first_run_records_baseline_and_notifies_nothing(tmp_path) -> None:
    _seed_location(tmp_path)
    result = headless_check.run_check(
        tmp_path, fetch_alerts=lambda _la, _lo: [_alert("a", "Flood Watch")]
    )
    assert result.checked is True
    assert result.is_baseline is True
    assert result.new_alerts == []
    assert monitor.load_notified_ids(tmp_path) == {"a"}  # baseline recorded


def test_second_run_reports_only_new_alerts(tmp_path) -> None:
    _seed_location(tmp_path)
    headless_check.run_check(tmp_path, fetch_alerts=lambda _la, _lo: [_alert("a", "Flood Watch")])
    result = headless_check.run_check(
        tmp_path,
        fetch_alerts=lambda _la, _lo: [
            _alert("a", "Flood Watch"),
            _alert("b", "Tornado Warning", "Extreme"),
        ],
    )
    assert [a.event for a in result.new_alerts] == ["Tornado Warning"]
    assert monitor.load_notified_ids(tmp_path) == {"a", "b"}


def test_already_notified_never_repeats(tmp_path) -> None:
    _seed_location(tmp_path)
    headless_check.run_check(tmp_path, fetch_alerts=lambda _la, _lo: [_alert("a", "Flood Watch")])
    again = headless_check.run_check(
        tmp_path, fetch_alerts=lambda _la, _lo: [_alert("a", "Flood Watch")]
    )
    assert again.new_alerts == []


def test_cleared_alert_drops_from_notified_set(tmp_path) -> None:
    # So that if the same id re-issues later it counts as new again.
    _seed_location(tmp_path)
    headless_check.run_check(tmp_path, fetch_alerts=lambda _la, _lo: [_alert("a", "Flood Watch")])
    headless_check.run_check(tmp_path, fetch_alerts=lambda _la, _lo: [])
    assert monitor.load_notified_ids(tmp_path) == set()


def test_skips_without_a_location(tmp_path) -> None:
    result = headless_check.run_check(tmp_path, fetch_alerts=lambda _la, _lo: [_alert("a", "X")])
    assert result.checked is False
    assert result.reason == "no location"


def test_skips_in_safe_mode(tmp_path) -> None:
    _seed_location(tmp_path)
    called: list[bool] = []
    result = headless_check.run_check(
        tmp_path, fetch_alerts=lambda _la, _lo: called.append(True) or [], safe_mode=True
    )
    assert result.checked is False
    assert called == []  # never even fetched


def test_toast_content_single_and_multi() -> None:
    single = headless_check.toast_content([_alert("a", "Tornado Warning")], "Tucson, AZ")
    assert single[0] == "Weather alert: Tornado Warning"
    multi = headless_check.toast_content(
        [_alert("a", "Tornado Warning", "Extreme"), _alert("b", "Flood Watch")], "Tucson, AZ"
    )
    assert multi[0] == "2 new weather alerts"
    assert "Most urgent: Tornado Warning" in multi[1]


def test_notified_ids_round_trip(tmp_path) -> None:
    assert monitor.notified_ids_exist(tmp_path) is False
    monitor.save_notified_ids(tmp_path, {"x", "y"})
    assert monitor.notified_ids_exist(tmp_path) is True
    assert monitor.load_notified_ids(tmp_path) == {"x", "y"}
