"""Tests for the wx-free Recordings Manager status model."""

from __future__ import annotations

from pathlib import Path

from quill.core.radio.recording import RecordingSettings
from quill.core.radio.recording_schedule import RecordingScheduleEntry
from quill.core.radio.recordings_index import (
    STATUS_RECORDED,
    STATUS_RECORDING,
    STATUS_SCHEDULED,
    list_recordings,
    recordings_dir,
)


def _settings(root: Path) -> RecordingSettings:
    return RecordingSettings(destination_root=str(root))


def test_missing_folder_lists_nothing(tmp_path: Path) -> None:
    assert list_recordings(_settings(tmp_path / "absent")) == []


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
    entries = list_recordings(_settings(tmp_path), active_path=active)
    assert entries[0].name == "active"
    assert entries[0].status == STATUS_RECORDING
    assert entries[1].status == STATUS_RECORDED


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


def test_recordings_dir_honors_override_and_default(tmp_path: Path) -> None:
    assert recordings_dir(_settings(tmp_path)) == tmp_path
    default = recordings_dir(RecordingSettings())
    assert default.name == "radio_recordings"
