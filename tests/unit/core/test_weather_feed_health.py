"""Alert-feed health: failure is never "no alerts", thresholds, once-only notices,
persistence, Safe Mode wording, and the headless check's use of all of it."""

from __future__ import annotations

import urllib.error
from datetime import UTC, datetime
from pathlib import Path

import pytest

from quill.core.weather import feed_health as fh
from quill.core.weather import feed_health_store as fhs
from quill.core.weather import headless_check, monitor
from quill.core.weather import locations as loc_store
from quill.core.weather.models import WeatherAlert, WeatherLocation
from quill.core.weather.nws import WeatherError

T0 = datetime(2026, 11, 27, 15, 0, tzinfo=UTC).timestamp()
MIN = 60.0


def _alert(alert_id: str = "a1", event: str = "Tornado Warning", severity: str = "Extreme"):
    return WeatherAlert(
        id=alert_id,
        event=event,
        severity=severity,
        urgency="Immediate",
        headline=f"{event} issued",
        area_description="Dane County; Iowa County",
        effective="2026-11-27T15:00:00Z",
        expires="2026-11-27T16:00:00Z",
    )


def _tracker() -> fh.FeedHealthTracker:
    return fh.FeedHealthTracker(tz=UTC)


def _fail(t: fh.FeedHealthTracker, at: float, place: str = "home") -> None:
    t.record_failure(place, "Home", fh.FailureKind.CONNECT, at)


# -- states and the "never an empty answer" rule -----------------------------


def test_never_checked_then_healthy_with_zero_alerts() -> None:
    t = _tracker()
    assert t.overall_state(T0, ["home"]) is fh.FeedState.NEVER
    t.record_success("home", "Home", [], T0)
    assert t.state_of("home", T0) is fh.FeedState.HEALTHY
    assert "no alerts" in t.status_text(["home"], {"home": "Home"}, T0).lower()


def test_failure_never_clears_last_alerts_or_success_time() -> None:
    t = _tracker()
    t.record_success("home", "Home", [_alert()], T0)
    for i in range(1, 6):
        _fail(t, T0 + i * 5 * MIN)
    health = t.places["home"]
    assert [a.event for a in health.last_alerts] == ["Tornado Warning"]
    assert health.last_success == T0


def test_failure_report_never_says_all_clear_and_labels_alerts_last_known() -> None:
    t = _tracker()
    t.record_success("home", "Home", [_alert()], T0)
    _fail(t, T0 + 20 * MIN)
    text = t.status_text(["home"], {"home": "Home"}, T0 + 20 * MIN)
    assert "last known" in text
    assert "Tornado Warning" in text
    assert "all clear" not in text.lower()
    assert "What went wrong" in text


def test_first_failure_is_degraded_not_unreachable() -> None:
    t = _tracker()
    t.record_success("home", "Home", [], T0)
    _fail(t, T0 + 5 * MIN)
    assert t.state_of("home", T0 + 5 * MIN) is fh.FeedState.DEGRADED


# -- threshold timing --------------------------------------------------------


def test_unreachable_needs_ten_minutes_and_three_attempts() -> None:
    t = _tracker()
    t.record_success("home", "Home", [], T0)
    _fail(t, T0 + 3 * MIN)
    _fail(t, T0 + 6 * MIN)
    _fail(t, T0 + 9 * MIN)  # three attempts, but only nine minutes
    assert t.state_of("home", T0 + 9 * MIN) is fh.FeedState.DEGRADED
    _fail(t, T0 + 10 * MIN)
    assert t.state_of("home", T0 + 10 * MIN) is fh.FeedState.UNREACHABLE


def test_ten_minutes_with_only_two_attempts_is_not_enough() -> None:
    t = _tracker()
    t.record_success("home", "Home", [], T0)
    _fail(t, T0 + 5 * MIN)
    _fail(t, T0 + 11 * MIN)
    assert t.state_of("home", T0 + 11 * MIN) is fh.FeedState.DEGRADED


def test_unreachable_comes_sooner_while_an_alert_is_active() -> None:
    t = _tracker()
    t.record_success("home", "Home", [_alert()], T0)
    _fail(t, T0 + 1 * MIN)
    _fail(t, T0 + 2 * MIN)
    assert t.state_of("home", T0 + 2 * MIN) is fh.FeedState.UNREACHABLE


def test_never_succeeded_counts_from_the_first_failure() -> None:
    t = _tracker()
    for i in range(3):
        _fail(t, T0 + i * 4 * MIN)
    assert t.state_of("home", T0 + 8 * MIN) is fh.FeedState.DEGRADED
    _fail(t, T0 + 12 * MIN)
    assert t.state_of("home", T0 + 12 * MIN) is fh.FeedState.UNREACHABLE


# -- announcements: once, repeat after 30 minutes, recovery once -------------


def _drive_to_unreachable(t: fh.FeedHealthTracker) -> float:
    t.record_success("home", "Home", [], T0)
    t.end_of_round(T0)
    now = T0
    for i in range(1, 4):
        now = T0 + i * 4 * MIN
        _fail(t, now)
    return now


def test_unreachable_is_announced_once_with_the_last_check_sentence() -> None:
    t = _tracker()
    now = _drive_to_unreachable(t)
    notice = t.end_of_round(now)
    assert notice is not None and notice.kind == "unreachable"
    assert notice.text == (
        "Quill Weather cannot reach the National Weather Service. Alerts may be missing. "
        "The last successful check was at 3:00 PM, and it found no alerts."
    )
    _fail(t, now + 4 * MIN)
    assert t.end_of_round(now + 4 * MIN) is None


def test_repeats_only_after_thirty_minutes_then_recovery_once() -> None:
    t = _tracker()
    now = _drive_to_unreachable(t)
    assert t.end_of_round(now) is not None
    _fail(t, now + 29 * MIN)
    assert t.end_of_round(now + 29 * MIN) is None
    _fail(t, now + 30 * MIN)
    again = t.end_of_round(now + 30 * MIN)
    assert again is not None and again.kind == "still_unreachable"
    t.record_success("home", "Home", [], now + 31 * MIN)
    back = t.end_of_round(now + 31 * MIN)
    assert back is not None and back.kind == "recovered"
    t.record_success("home", "Home", [], now + 32 * MIN)
    assert t.end_of_round(now + 32 * MIN) is None


def test_no_recovery_notice_when_nothing_was_announced() -> None:
    t = _tracker()
    t.record_success("home", "Home", [], T0)
    _fail(t, T0 + MIN)
    t.record_success("home", "Home", [], T0 + 2 * MIN)
    assert t.end_of_round(T0 + 2 * MIN) is None


def test_message_without_any_success_says_so() -> None:
    t = _tracker()
    for i in range(4):
        _fail(t, T0 + i * 4 * MIN)
    notice = t.end_of_round(T0 + 12 * MIN)
    assert notice is not None
    assert "has not been a successful check yet" in notice.text


# -- Safe Mode ----------------------------------------------------------------


def test_safe_mode_says_checks_are_off_not_unreachable() -> None:
    t = fh.FeedHealthTracker(safe_mode=True, tz=UTC)
    assert t.overall_state(T0) is fh.FeedState.CHECKS_OFF
    assert t.end_of_round(T0) is None
    text = t.status_text(["home"], {"home": "Home"}, T0)
    assert "Network checks are off" in text
    assert "unreachable" not in text.lower() and "cannot reach" not in text.lower()
    assert "Safe Mode" in t.summary(T0, ["home"])


# -- classification -----------------------------------------------------------


def _wrapped(cause: BaseException) -> WeatherError:
    error = WeatherError("Could not reach the weather service")
    error.__cause__ = cause
    return error


@pytest.mark.parametrize(
    ("error", "kind"),
    [
        (_wrapped(urllib.error.URLError("no route")), fh.FailureKind.CONNECT),
        (_wrapped(TimeoutError()), fh.FailureKind.CONNECT),
        (
            _wrapped(urllib.error.HTTPError("https://x", 503, "busy", {}, None)),  # type: ignore[arg-type]
            fh.FailureKind.SERVICE,
        ),
        (
            _wrapped(urllib.error.HTTPError("https://x", 429, "slow down", {}, None)),  # type: ignore[arg-type]
            fh.FailureKind.SERVICE,
        ),
        (_wrapped(ValueError("bad json")), fh.FailureKind.UNREADABLE),
        (
            WeatherError("Weather is a network service and is disabled in Safe Mode."),
            fh.FailureKind.SAFE_MODE,
        ),
    ],
)
def test_classify_failure(error: BaseException, kind: fh.FailureKind) -> None:
    assert fh.classify_failure(error)[0] is kind


# -- persistence --------------------------------------------------------------


def test_round_trip_keeps_success_time_alerts_and_warning(tmp_path: Path) -> None:
    t = _tracker()
    t.record_success("home", "Home", [_alert()], T0)
    _fail(t, T0 + 5 * MIN)
    t.warned_at = T0 + 6 * MIN
    fhs.save_tracker(tmp_path, t)
    loaded = fhs.load_tracker(tmp_path, tz=UTC)
    health = loaded.places["home"]
    assert health.last_success == T0
    assert health.consecutive_failures == 1
    assert health.last_failure_kind is fh.FailureKind.CONNECT
    assert health.last_alerts[0].event == "Tornado Warning"
    assert loaded.warned_at == T0 + 6 * MIN


def test_damaged_file_is_kept_aside_and_reads_as_never_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kept: list[str] = []
    monkeypatch.setattr(
        "quill.core.migration_backup.backup_corrupt_file", lambda name, path: kept.append(name)
    )
    fhs.store_path(tmp_path).write_text("{not json", encoding="utf-8")
    loaded = fhs.load_tracker(tmp_path)
    assert loaded.places == {}
    assert kept == ["weather_feed_health"]


def test_persisted_data_is_bounded() -> None:
    t = _tracker()
    many = [_alert(f"id{i}") for i in range(80)]
    t.record_success("home", "Home", many, T0)
    assert len(t.places["home"].last_alerts) == fh.MAX_ALERTS_PER_PLACE
    for i in range(80):
        t.record_success(f"p{i}", f"P{i}", [], T0)
    assert len(t.to_json()["places"]) == fh.MAX_PLACES


# -- as-of and start summary -------------------------------------------------


def test_as_of_phrase_only_for_old_data() -> None:
    t = _tracker()
    t.record_success("home", "Home", [], T0)
    assert t.as_of_phrase(["home"], T0 + MIN) == ""
    assert t.as_of_phrase(["home"], T0 + 20 * MIN) == " As of 3:00 PM."


def test_start_summary_never_counts_a_failed_place_as_clear() -> None:
    config = monitor.MonitorConfig()
    text = monitor.start_summary_multi(
        {"Home": 0},
        config,
        {"Work": "The last successful check was at 3:00 PM, and it found no alerts."},
    )
    assert "Could not check Work" in text
    assert "All clear" not in text
    assert "3:00 PM" in text


def test_start_summary_when_every_place_failed() -> None:
    text = monitor.start_summary_multi({}, monitor.MonitorConfig(), {"Home": ""})
    assert "could not reach" in text
    assert "No active alerts" not in text and "All clear" not in text


# -- tooltip --------------------------------------------------------------------


def test_tooltip_reflects_state() -> None:
    t = _tracker()
    assert "no alert check yet" in t.tooltip(T0)
    t.record_success("home", "Home", [], T0)
    assert "working" in t.tooltip(T0)
    now = _drive_to_unreachable(t)
    assert "cannot reach" in t.tooltip(now)


# -- the headless check ---------------------------------------------------------


def _store_with_place(tmp_path: Path) -> None:
    store = loc_store.load_locations(tmp_path)
    store.add(WeatherLocation(id="home", display_name="Home", latitude=43.0, longitude=-89.0))
    loc_store.save_locations(tmp_path, store)


def test_headless_failure_is_recorded_and_notified_once_then_recovers(tmp_path: Path) -> None:
    _store_with_place(tmp_path)
    clock = {"now": T0}
    notices: list[fh.Notice] = []

    def good(_lat: float, _lon: float) -> list[WeatherAlert]:
        return []

    def bad(_lat: float, _lon: float) -> list[WeatherAlert]:
        raise _wrapped(urllib.error.URLError("down"))

    kw = {"now": lambda: clock["now"], "on_notice": notices.append}
    headless_check.run_check(tmp_path, fetch_alerts=good, **kw)  # type: ignore[arg-type]
    for i in range(1, 5):
        clock["now"] = T0 + i * 4 * MIN
        with pytest.raises(WeatherError):
            headless_check.run_check(tmp_path, fetch_alerts=bad, **kw)  # type: ignore[arg-type]
    assert [n.kind for n in notices] == ["unreachable"]
    saved = fhs.load_tracker(tmp_path)
    assert saved.places["home"].last_success == T0  # failure never replaced it
    clock["now"] = T0 + 25 * MIN
    headless_check.run_check(tmp_path, fetch_alerts=good, **kw)  # type: ignore[arg-type]
    assert [n.kind for n in notices] == ["unreachable", "recovered"]


def test_headless_failure_does_not_speak_all_clear_or_clear_alerts(tmp_path: Path) -> None:
    _store_with_place(tmp_path)

    def one(_lat: float, _lon: float) -> list[WeatherAlert]:
        return [_alert()]

    def bad(_lat: float, _lon: float) -> list[WeatherAlert]:
        raise _wrapped(TimeoutError())

    headless_check.run_check(tmp_path, fetch_alerts=one, now=lambda: T0)
    with pytest.raises(WeatherError):
        headless_check.run_check(tmp_path, fetch_alerts=bad, now=lambda: T0 + MIN)
    assert fhs.load_tracker(tmp_path).places["home"].last_alerts[0].id == "a1"
    assert "a1" in monitor.load_notified_ids(tmp_path)
