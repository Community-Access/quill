"""Headless tests for R3 recording resume: marker persistence, temp-dir
reconcile, remaining/grace math, and the RadioHistory resume-choice field.

Pure/wx-free; the resume dialog itself is exercised via the shared dialog
contract in CI (no desktop UI automation locally)."""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from pathlib import Path

from quill.core.radio.recording import RecordingSettings
from quill.core.radio.recording_resume import (
    DEFAULT_RESUME_GRACE_MINUTES,
    ActiveRecordingMarker,
    clear_marker,
    load_marker,
    reconcile_temp_strays,
    remaining_minutes,
    save_marker,
    within_resume_grace,
)


def _marker(
    *,
    started: datetime,
    minutes: int = 60,
    station: str = "WQXR",
    url: str = "https://x/stream",
    temp: str = "",
    output: str = "",
    entry_id: str = "",
) -> ActiveRecordingMarker:
    return ActiveRecordingMarker(
        station_name=station,
        stream_url=url,
        temp_path=temp,
        output_path=output,
        started_at=started.isoformat(),
        scheduled_end=(started + timedelta(minutes=minutes)).isoformat(),
        duration_minutes=minutes,
        entry_id=entry_id,
    )


def _settings(root: Path, *, temp: str = "") -> RecordingSettings:
    return RecordingSettings(destination_root=str(root), temp_dir=temp)


# -- marker persistence --------------------------------------------------------


def test_save_load_and_clear_marker_round_trip(tmp_path: Path) -> None:
    marker = _marker(started=datetime(2026, 7, 17, 8, 0), temp="/t/a.mp3", output="/o/a.mp3")
    save_marker(tmp_path, marker)
    reloaded = load_marker(tmp_path)
    assert reloaded is not None
    assert reloaded.stream_url == "https://x/stream"
    assert reloaded.temp_path == "/t/a.mp3"
    assert reloaded.duration_minutes == 60
    clear_marker(tmp_path)
    assert load_marker(tmp_path) is None
    # Clearing an absent marker is not an error.
    clear_marker(tmp_path)


def test_load_marker_absent_or_corrupt_returns_none(tmp_path: Path) -> None:
    assert load_marker(tmp_path) is None
    (tmp_path / "radio_active_recording.json").write_text("not json", encoding="utf-8")
    assert load_marker(tmp_path) is None


def test_marker_from_dict_tolerates_missing_and_bad_fields() -> None:
    # An empty dict yields a default marker (all fields coerce to "" / 0).
    assert ActiveRecordingMarker.from_dict({}) is not None
    # A non-numeric duration is a corrupt marker -> discarded whole (load_marker
    # then reads as None, so a bad marker never drives a bogus resume).
    assert ActiveRecordingMarker.from_dict({"duration_minutes": "oops"}) is None


# -- remaining / grace ---------------------------------------------------------


def test_remaining_minutes_shrinks_and_floors_at_zero() -> None:
    started = datetime(2026, 7, 17, 8, 0)
    marker = _marker(started=started, minutes=60)
    assert remaining_minutes(marker, datetime(2026, 7, 17, 8, 0)) == 60
    assert remaining_minutes(marker, datetime(2026, 7, 17, 8, 30)) == 30
    # Past the end -> 0 (show is over).
    assert remaining_minutes(marker, datetime(2026, 7, 17, 9, 30)) == 0


def test_within_resume_grace_covers_window_and_short_overshoot() -> None:
    started = datetime(2026, 7, 17, 8, 0)
    marker = _marker(started=started, minutes=60)  # ends 09:00
    assert within_resume_grace(marker, datetime(2026, 7, 17, 8, 30)) is True
    # Just past the end, within the default grace -> still offered.
    assert within_resume_grace(marker, datetime(2026, 7, 17, 9, 5)) is True
    # Well past the grace window -> not offered.
    assert within_resume_grace(marker, datetime(2026, 7, 17, 9, 30), grace_minutes=10) is False


# -- reconcile temp strays -----------------------------------------------------


def _age(path: Path, seconds: float) -> None:
    when = time.time() - seconds
    os.utime(path, (when, when))


def test_reconcile_moves_finished_orphans_to_destination(tmp_path: Path) -> None:
    dest = tmp_path / "recordings"
    temp = tmp_path / "scratch"
    dest.mkdir()
    temp.mkdir()
    orphan = temp / "show.mp3"
    orphan.write_bytes(b"x")
    _age(orphan, 120)  # older than the still-writing cutoff -> finished orphan
    moved = reconcile_temp_strays(_settings(dest, temp=str(temp)))
    assert moved == [dest / "show.mp3"]
    assert (dest / "show.mp3").exists()
    assert not orphan.exists()


def test_reconcile_leaves_a_file_still_being_written(tmp_path: Path) -> None:
    dest = tmp_path / "recordings"
    temp = tmp_path / "scratch"
    dest.mkdir()
    temp.mkdir()
    live = temp / "live.mp3"
    live.write_bytes(b"x")
    _age(live, 5)  # recent mtime -> treated as still being written
    moved = reconcile_temp_strays(_settings(dest, temp=str(temp)))
    assert moved == []
    assert live.exists()  # left in temp, untouched


def test_reconcile_ignores_non_recording_files_and_no_temp_dir(tmp_path: Path) -> None:
    dest = tmp_path / "recordings"
    dest.mkdir()
    # No temp dir set -> no-op.
    assert reconcile_temp_strays(_settings(dest)) == []
    temp = tmp_path / "scratch"
    temp.mkdir()
    (temp / "notes.txt").write_text("ignore me", encoding="utf-8")
    _age(temp / "notes.txt", 120)
    assert reconcile_temp_strays(_settings(dest, temp=str(temp))) == []
    assert (dest / "notes.txt").exists() is False


def test_reconcile_temp_equal_destination_is_noop(tmp_path: Path) -> None:
    same = tmp_path / "both"
    same.mkdir()
    (same / "show.mp3").write_bytes(b"x")
    _age(same / "show.mp3", 120)
    assert reconcile_temp_strays(_settings(same, temp=str(same))) == []


# -- RadioHistory.recording_resume_choice -------------------------------------


def test_history_recording_resume_choice_round_trips(tmp_path: Path) -> None:
    from quill.core.radio import history as radio_history

    radio_history.save_history(tmp_path, radio_history.RadioHistory())
    loaded = radio_history.load_history(tmp_path)
    assert loaded.recording_resume_choice == "ask"

    hist = radio_history.RadioHistory()
    hist.recording_resume_choice = "always"
    radio_history.save_history(tmp_path, hist)
    assert radio_history.load_history(tmp_path).recording_resume_choice == "always"

    # A bad value degrades to "ask".
    (tmp_path / "radio_history.json").write_text(
        '{"recording_resume_choice": "yesterday"}', encoding="utf-8"
    )
    assert radio_history.load_history(tmp_path).recording_resume_choice == "ask"


def test_default_grace_is_ten_minutes() -> None:
    assert DEFAULT_RESUME_GRACE_MINUTES == 10
