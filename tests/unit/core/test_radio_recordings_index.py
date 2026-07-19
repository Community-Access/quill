"""Tests for the wx-free Recordings Manager status model."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from quill.core.radio.recording import RecordingSettings
from quill.core.radio.recording_schedule import RecordingScheduleEntry
from quill.core.radio.recordings_index import (
    STATUS_COMPLETED,
    STATUS_RECORDED,
    STATUS_RECORDING,
    STATUS_SCHEDULED,
    ActiveRecording,
    format_elapsed,
    list_recordings,
    recordings_dir,
)


def _settings(root: Path) -> RecordingSettings:
    return RecordingSettings(destination_root=str(root))


def _active(
    path: Path, *, station: str = "Live", url: str = "https://x", started=None
) -> ActiveRecording:
    return ActiveRecording(path=path, station_name=station, stream_url=url, started_at=started)


def test_missing_folder_lists_nothing(tmp_path: Path) -> None:
    assert list_recordings(_settings(tmp_path / "absent")) == []


def test_multiple_active_recordings_each_lead_as_own_row(tmp_path: Path) -> None:
    # Concurrent recording: a list of active recordings yields one Recording row
    # each, carrying its job id, oldest first as passed.
    a = tmp_path / "A - live.mp3"
    b = tmp_path / "B - live.mp3"
    a.write_bytes(b"a")
    b.write_bytes(b"b")
    actives = [
        ActiveRecording(path=a, station_name="A", stream_url="https://x/a", job_id="ja"),
        ActiveRecording(path=b, station_name="B", stream_url="https://x/b", job_id="jb"),
    ]
    rows = list_recordings(_settings(tmp_path), active=actives)
    recording_rows = [r for r in rows if r.status == STATUS_RECORDING]
    assert [r.name for r in recording_rows] == ["A", "B"]
    assert [r.job_id for r in recording_rows] == ["ja", "jb"]
    # Neither active file is also listed as Recorded (no double-listing).
    assert sum(1 for r in rows if r.status == STATUS_RECORDED) == 0


def test_scheduled_suppressed_while_its_stream_is_one_of_the_actives(tmp_path: Path) -> None:
    active = ActiveRecording(
        path=tmp_path / "B - live.mp3", station_name="B", stream_url="https://x/b", job_id="jb"
    )
    (tmp_path / "B - live.mp3").write_bytes(b"b")
    scheduled = [
        RecordingScheduleEntry(
            id="s1",
            station_name="B",
            stream_url="https://x/b",
            recurrence="daily",
            run_at="2026-07-14T08:00:00",
        )
    ]
    rows = list_recordings(_settings(tmp_path), active=[active], scheduled=scheduled)
    # The firing schedule is the Recording row, not also a Scheduled row.
    assert not any(r.status == STATUS_SCHEDULED for r in rows)


def test_files_list_newest_first_with_status_recorded(tmp_path: Path) -> None:
    older = tmp_path / "Morning Show 2026-07-13.mp3"
    newer = tmp_path / "Jazz Night 2026-07-14.mp3"
    older.write_bytes(b"a" * 10)
    newer.write_bytes(b"b" * 2048)
    import os
    import time

    now = time.time()
    os.utime(older, (now - 100, now - 100))
    os.utime(newer, (now, now))
    entries = list_recordings(_settings(tmp_path))
    assert [e.name for e in entries] == ["Jazz Night 2026-07-14", "Morning Show 2026-07-13"]
    assert all(e.status == STATUS_RECORDED for e in entries)
    assert entries[0].size_display.endswith("KB")


def test_non_recording_files_are_ignored(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("not audio", encoding="utf-8")
    (tmp_path / "show.mp3").write_bytes(b"x")
    entries = list_recordings(_settings(tmp_path))
    assert [e.name for e in entries] == ["show"]


def test_active_recording_leads_the_list(tmp_path: Path) -> None:
    done = tmp_path / "done.mp3"
    active = tmp_path / "active.mp3"
    done.write_bytes(b"x")
    active.write_bytes(b"y")
    entries = list_recordings(_settings(tmp_path), active=_active(active, station="active"))
    assert entries[0].name == "active"
    assert entries[0].status == STATUS_RECORDING
    assert entries[1].status == STATUS_RECORDED
    # Identity is the resolved path, so a status flip keeps the same row key.
    assert entries[0].id == str(active.resolve())


def test_active_recording_shown_even_when_in_a_temp_dir(tmp_path: Path) -> None:
    # R1/10.3: with a temp dir set, the active file lives in temp and the folder
    # scan (of the destination) never sees it -- but the active row must still
    # appear, found by identity from the recorder state.
    dest = tmp_path / "recordings"
    temp = tmp_path / "scratch"
    dest.mkdir()
    temp.mkdir()
    active = temp / "show.mp3"
    active.write_bytes(b"writing")
    entries = list_recordings(_settings(dest), active=_active(active, station="show"))
    assert entries[0].status == STATUS_RECORDING
    assert entries[0].name == "show"
    assert entries[0].path == active
    # The temp file is not also emitted as Recorded (no double-listing).
    assert all(e.status != STATUS_RECORDED or e.path != active for e in entries)


def test_active_row_carries_started_at_for_elapsed(tmp_path: Path) -> None:
    started = datetime.now() - timedelta(seconds=65)
    active = tmp_path / "live.mp3"
    active.write_bytes(b"x")
    entries = list_recordings(
        _settings(tmp_path), active=_active(active, station="live", started=started)
    )
    assert entries[0].started_at == started


def test_completed_once_entry_is_completed_not_scheduled(tmp_path: Path) -> None:
    # R1/10.1: a one-time schedule that already ran shows as Completed and is
    # excluded from the scheduled count (R2 also auto-disables it; this is the
    # legacy path for schedules saved before that).
    fired = RecordingScheduleEntry(
        id="1",
        station_name="WQXR",
        stream_url="https://x",
        recurrence="once",
        run_at="2026-07-20T07:00",
        last_fired_date="2026-07-20",
    )
    entries = list_recordings(_settings(tmp_path), scheduled=[fired])
    assert len(entries) == 1
    assert entries[0].status == STATUS_COMPLETED
    assert entries[0].path is None


def test_scheduled_entries_append_with_recurrence_detail(tmp_path: Path) -> None:
    once = RecordingScheduleEntry(
        id="1",
        station_name="WQXR",
        stream_url="https://x",
        recurrence="once",
        run_at="2026-07-20T07:00",
    )
    disabled = RecordingScheduleEntry(
        id="2",
        station_name="Off",
        stream_url="https://y",
        recurrence="daily",
        run_at="2026-07-20T08:00",
        enabled=False,
    )
    entries = list_recordings(_settings(tmp_path), scheduled=[once, disabled])
    assert len(entries) == 1
    entry = entries[0]
    assert entry.status == STATUS_SCHEDULED
    assert entry.name == "WQXR"
    assert "once at 2026-07-20 07:00" in entry.detail
    assert entry.path is None
    assert entry.id == "schedule:1"


def test_scheduled_detail_carries_zone_offset_label(tmp_path: Path) -> None:
    # R1/10.6: a zoned scheduled entry shows its UTC offset so a cross-zone
    # entry reads correctly in the Recordings dialog.
    entry = RecordingScheduleEntry(
        id="z1",
        station_name="WQXR",
        stream_url="https://x",
        recurrence="daily",
        run_at="2026-01-01T19:00",
        timezone="America/New_York",
    )
    rows = list_recordings(_settings(tmp_path), scheduled=[entry], now=datetime(2026, 7, 14, 12, 0))
    assert rows[0].status == STATUS_SCHEDULED
    assert "UTC-4" in rows[0].detail  # July -> EDT


def test_firing_schedule_is_not_double_counted_as_scheduled(tmp_path: Path) -> None:
    # R1/10.2: while this stream is the one recording, the firing schedule is
    # the Recording row -- it must not also appear as Scheduled.
    active = tmp_path / "live.mp3"
    active.write_bytes(b"x")
    firing = RecordingScheduleEntry(
        id="s1",
        station_name="WQXR",
        stream_url="https://x/stream",
        recurrence="daily",
        run_at="2026-01-01T08:00",
    )
    other = RecordingScheduleEntry(
        id="s2",
        station_name="Other",
        stream_url="https://other/stream",
        recurrence="daily",
        run_at="2026-01-01T09:00",
    )
    entries = list_recordings(
        _settings(tmp_path),
        active=_active(active, url="https://x/stream"),
        scheduled=[firing, other],
    )
    assert entries[0].status == STATUS_RECORDING
    # The firing schedule is suppressed; the unrelated one still shows.
    statuses = [e.status for e in entries]
    assert statuses.count(STATUS_SCHEDULED) == 1
    assert entries[-1].name == "Other"


def test_recordings_dir_honors_override_and_default(tmp_path: Path) -> None:
    assert recordings_dir(_settings(tmp_path)) == tmp_path
    default = recordings_dir(RecordingSettings())
    assert default.name == "Quill Radio Recordings"


def test_format_elapsed_mmss_and_hmmss() -> None:
    # R1/10.4: elapsed readout formatting.
    start = datetime(2026, 7, 14, 8, 0, 0)
    assert format_elapsed(start, datetime(2026, 7, 14, 8, 0, 5)) == "00:05"
    assert format_elapsed(start, datetime(2026, 7, 14, 8, 1, 0)) == "01:00"
    assert format_elapsed(start, datetime(2026, 7, 14, 9, 2, 3)) == "1:02:03"
    # Never negative -- a clock skew or a future start clamps to zero.
    assert format_elapsed(start, datetime(2026, 7, 14, 7, 59, 0)) == "00:00"
