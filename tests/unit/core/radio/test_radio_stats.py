"""Listening statistics for Quill Radio: what counts, and what does not.

The one that matters is the clock. A statistics window that counts connecting,
buffering, paused or stopped time is worse than none, because it is confidently
wrong about the only number it exists to report.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from quill.core import media_stats
from quill.core.radio import stats
from quill.core.radio.models import RadioStation


def _station(name: str, uuid: str = "") -> RadioStation:
    return RadioStation(
        name=name,
        stream_url=f"https://example.com/{name.lower()}",
        station_uuid=uuid,
        source="ACB Media",
    )


def test_a_station_is_keyed_the_way_favorites_keys_it() -> None:
    """Otherwise a favorite and its totals fork into two rows for one station."""
    from quill.core.radio.favorites import FavoriteStation

    station = _station("WQXR", uuid="abc-123")
    assert stats.station_key(station) == FavoriteStation(station=station).key


def test_a_session_is_recorded_and_totalled(tmp_path: Path) -> None:
    stats.record_listen(tmp_path, _station("WQXR"), 1800, network="ACB Media")
    stats.record_listen(tmp_path, _station("WQXR"), 900, network="ACB Media")
    stats.record_listen(tmp_path, _station("KFI"), 600, network="Talk")

    summary = stats.summarize(tmp_path)
    assert summary.total_seconds == 3300
    assert summary.sessions == 3
    assert [total.seconds for total in summary.keys] == [2700, 600]


def test_the_network_is_totalled_too(tmp_path: Path) -> None:
    """ "Four hours of ACB Media" is a fact no per-station row adds up for you."""
    stats.record_listen(tmp_path, _station("WQXR"), 1800, network="ACB Media")
    stats.record_listen(tmp_path, _station("KFI"), 600, network="Talk")
    summary = stats.summarize(tmp_path)
    assert [(total.key, total.seconds) for total in summary.groups] == [
        ("ACB Media", 1800),
        ("Talk", 600),
    ]


def test_a_zero_length_stretch_is_not_a_session(tmp_path: Path) -> None:
    stats.record_listen(tmp_path, _station("WQXR"), 0)
    assert stats.load_sessions(tmp_path) == []


def test_speed_and_trimming_are_absent_for_a_live_stream(tmp_path: Path) -> None:
    """You cannot listen to a broadcast at 1.4x, and there is no silence to cut."""
    stats.record_listen(tmp_path, _station("WQXR"), 60)
    summary = stats.summarize(tmp_path)
    assert summary.saved_by_speed_seconds == 0
    assert summary.trim_measured is False
    lines = " ".join(stats.describe(summary))
    assert "speed" not in lines.lower()
    assert "trim" not in lines.lower()


def test_a_period_only_counts_what_falls_inside_it(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    stats.record_listen(tmp_path, _station("WQXR"), 600, now=now)
    stats.record_listen(tmp_path, _station("KFI"), 600, now=now - timedelta(days=40))
    assert stats.summarize(tmp_path, period="week", now=now).total_seconds == 600
    assert stats.summarize(tmp_path, period="all", now=now).total_seconds == 1200


def test_an_empty_period_says_so_rather_than_reading_as_broken(tmp_path: Path) -> None:
    lines = stats.describe(stats.summarize(tmp_path))
    assert "Nothing listened to yet" in " ".join(lines)


def test_history_can_be_deleted(tmp_path: Path) -> None:
    stats.record_listen(tmp_path, _station("WQXR"), 600)
    assert stats.clear_sessions(tmp_path) == 1
    assert stats.load_sessions(tmp_path) == []


def test_radio_and_cast_keep_separate_logs() -> None:
    from quill.core.podcasts.stats import _FILE_NAME as cast_file

    assert stats.FILE_NAME != cast_file


def test_durations_are_words_not_a_time_of_day() -> None:
    """A screen reader reads 3:47:00 as "three forty-seven zero zero"."""
    assert media_stats.format_duration(3600 * 3 + 47 * 60) == "3 hours, 47 minutes"
    assert media_stats.format_duration(30) == "30 seconds"
    assert media_stats.format_duration(0) == "0 seconds"


def test_both_apps_mean_the_same_thing_by_this_week() -> None:
    from quill.core.podcasts.stats import PERIODS as cast_periods

    assert media_stats.PERIODS is cast_periods


# -- the clock ---------------------------------------------------------------


class _State:
    def __init__(self, name: str, station: Any) -> None:
        self.state = type("S", (), {"name": name})()
        self.station = station


class _Host:
    def __init__(self) -> None:
        self.said: list[str] = []

    def _announce(self, message: str) -> None:
        self.said.append(message)


def test_only_playing_time_counts(monkeypatch: Any, tmp_path: Path) -> None:
    from quill.ui.radio import stats_session

    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(stats_session, "MIN_SESSION_SECONDS", 0.0)
    clock = {"now": 1000.0}
    monkeypatch.setattr(stats_session.time, "monotonic", lambda: clock["now"])

    host = _Host()
    station = _station("WQXR")

    # Connecting: no clock.
    stats_session.on_state_changed(host, _State("CONNECTING", station))
    clock["now"] += 30
    assert stats.load_sessions(tmp_path) == []

    # Playing: the clock runs.
    stats_session.on_state_changed(host, _State("PLAYING", station))
    clock["now"] += 600
    stats_session.on_state_changed(host, _State("PAUSED", station))
    sessions = stats.load_sessions(tmp_path)
    assert len(sessions) == 1
    assert sessions[0].seconds == 600

    # Paused time does not accumulate.
    clock["now"] += 900
    stats_session.on_state_changed(host, _State("STOPPED", station))
    assert len(stats.load_sessions(tmp_path)) == 1


def test_changing_station_flushes_the_previous_one(monkeypatch: Any, tmp_path: Path) -> None:
    from quill.ui.radio import stats_session

    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(stats_session, "MIN_SESSION_SECONDS", 0.0)
    clock = {"now": 0.0}
    monkeypatch.setattr(stats_session.time, "monotonic", lambda: clock["now"])

    host = _Host()
    stats_session.on_state_changed(host, _State("PLAYING", _station("WQXR")))
    clock["now"] += 300
    stats_session.on_state_changed(host, _State("PLAYING", _station("KFI")))
    clock["now"] += 120
    stats_session.flush(host)

    summary = stats.summarize(tmp_path)
    assert sorted(total.seconds for total in summary.keys) == [120, 300]


def test_skipping_past_a_station_is_not_listening(monkeypatch: Any, tmp_path: Path) -> None:
    """A log full of three-second samples makes every per-station total a lie."""
    from quill.ui.radio import stats_session

    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    clock = {"now": 0.0}
    monkeypatch.setattr(stats_session.time, "monotonic", lambda: clock["now"])

    host = _Host()
    stats_session.on_state_changed(host, _State("PLAYING", _station("WQXR")))
    clock["now"] += 3
    stats_session.on_state_changed(host, _State("STOPPED", None))
    assert stats.load_sessions(tmp_path) == []
