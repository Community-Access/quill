"""Tests for the wx-free quill_radio_mac.core.recordings_index status
model: folder scan, active-recording detection, and scheduled-entry
merging (no ffmpeg, no network)."""

from __future__ import annotations

import os
import time
from pathlib import Path

from quill_radio_mac.core.recording import RecordingSettings
from quill_radio_mac.core.recording_schedule import RecordingScheduleEntry
from quill_radio_mac.core.recordings_index import (
    STATUS_RECORDED,
    STATUS_RECORDING,
    STATUS_SCHEDULED,
    list_recordings,
    recordings_dir,
)


def _settings(root: Path) -> RecordingSettings:
    return RecordingSettings(destination_root=str(root))


def test_missing_folder_lists_nothing(tmp_path: Path):
    assert list_recordings(_settings(tmp_path / "absent")) == []


def test_files_list_newest_first_with_status_recorded(tmp_path: Path):
    older = tmp_path / "Morning Show 2026-07-13.mp3"
    newer = tmp_path / "Jazz Night 2026-07-14.mp3"
    older.write_bytes(b"a" * 10)
    newer.write_bytes(b"b" * 2048)
    now = time.time()
    os.utime(older, (now - 100, now - 100))
    os.utime(newer, (now, now))
    entries = list_recordings(_settings(tmp_path))
    assert [e.name for e in entries] == ["Jazz Night 2026-07-14", "Morning Show 2026-07-13"]
    assert all(e.status == STATUS_RECORDED for e in entries)
    assert entries[0].size_display.endswith("KB")


def test_non_recording_files_are_ignored(tmp_path: Path):
    (tmp_path / "notes.txt").write_text("not audio", encoding="utf-8")
    (tmp_path / "show.mp3").write_bytes(b"x")
    entries = list_recordings(_settings(tmp_path))
    assert [e.name for e in entries] == ["show"]


def test_active_recording_leads_the_list(tmp_path: Path):
    done = tmp_path / "done.mp3"
    active = tmp_path / "active.mp3"
    done.write_bytes(b"x")
    active.write_bytes(b"y")
    entries = list_recordings(_settings(tmp_path), active_path=active)
    assert entries[0].name == "active"
    assert entries[0].status == STATUS_RECORDING
    assert entries[0].detail == "writing now"
    assert entries[1].status == STATUS_RECORDED


def test_scheduled_entries_append_with_recurrence_detail(tmp_path: Path):
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


def test_weekly_scheduled_entry_detail_shows_recurrence_and_time(tmp_path: Path):
    weekly = RecordingScheduleEntry(
        id="3",
        station_name="Sunday Jazz",
        stream_url="https://z",
        recurrence="weekly",
        run_at="2026-01-04T09:00",
        weekday=6,
    )
    entries = list_recordings(_settings(tmp_path), scheduled=[weekly])
    assert entries[0].detail == "weekly at 09:00"


def test_recordings_dir_honors_override_and_default(monkeypatch, tmp_path: Path):
    assert recordings_dir(_settings(tmp_path)) == tmp_path
    # No destination_root override: falls back to <data>/radio_recordings.
    # QUILL_DATA_DIR is set so this never touches the real user's home dir.
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "data"))
    default = recordings_dir(RecordingSettings())
    assert default == tmp_path / "data" / "radio_recordings"


def test_recording_entry_spoken_summary_includes_size_and_detail(tmp_path: Path):
    active = tmp_path / "active.mp3"
    active.write_bytes(b"x" * 10)
    entries = list_recordings(_settings(tmp_path), active_path=active)
    summary = entries[0].spoken_summary
    assert "active" in summary
    assert "recording" in summary
    assert "writing now" in summary


def test_size_display_bytes_and_mb_units():
    from quill_radio_mac.core.recordings_index import RecordingEntry

    small = RecordingEntry(name="a", status=STATUS_RECORDED, path=Path("a.mp3"), size_bytes=500)
    assert small.size_display == "500 bytes"
    big = RecordingEntry(
        name="b", status=STATUS_RECORDED, path=Path("b.mp3"), size_bytes=5 * 1024 * 1024
    )
    assert big.size_display == "5.0 MB"
    scheduled = RecordingEntry(name="c", status=STATUS_SCHEDULED, path=None)
    assert scheduled.size_display == ""
