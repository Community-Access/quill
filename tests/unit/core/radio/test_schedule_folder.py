"""A folder per scheduled recording (quill-radio #21).

The saved field round-trips, a schedule saved before the field existed loads
with the default folder, a folder that cannot be written is refused in plain
words, and a scheduled recording actually lands where its schedule says --
through the real recorder, with ffmpeg faked.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path

import pytest

import quill.core.radio.recording as recording
import quill.core.radio.schedule_folder as schedule_folder
from quill.core.radio.recording import RadioRecorder, RecordingSettings
from quill.core.radio.recording_schedule import (
    RecordingScheduleEntry,
    RecordingScheduler,
    load_schedule,
    save_schedule,
)
from quill.core.radio.schedule_folder import folder_problem, settings_for_folder


def _entry(**overrides: object) -> RecordingScheduleEntry:
    base: dict[str, object] = dict(
        id="e1",
        station_name="WXYZ",
        stream_url="https://example.com/stream",
        recurrence="daily",
        run_at="2026-07-14T08:00:00",
        duration_minutes=60,
    )
    base.update(overrides)
    return RecordingScheduleEntry(**base)  # type: ignore[arg-type]


# -- persistence ------------------------------------------------------------- #


def test_the_folder_round_trips(tmp_path: Path) -> None:
    jazz = str(tmp_path / "Jazz")
    save_schedule(tmp_path, [_entry(folder=jazz), _entry(id="e2")])
    loaded = load_schedule(tmp_path)
    assert [e.folder for e in loaded] == [jazz, ""]


def test_a_schedule_saved_before_folders_existed_loads_unchanged() -> None:
    old = _entry().to_dict()
    del old["folder"]
    entry = RecordingScheduleEntry.from_dict(old)
    assert entry is not None
    assert entry.folder == ""
    assert entry == _entry()


def test_a_null_folder_reads_as_the_default() -> None:
    data = _entry().to_dict()
    data["folder"] = None
    entry = RecordingScheduleEntry.from_dict(data)
    assert entry is not None and entry.folder == ""


# -- choosing the folder ---------------------------------------------------- #


def test_an_empty_folder_keeps_the_recording_settings() -> None:
    settings = RecordingSettings(destination_root="D:/Recordings")
    assert settings_for_folder(settings, "  ") is settings


def test_a_folder_replaces_only_the_destination() -> None:
    settings = RecordingSettings(destination_root="D:/Recordings", format="ogg")
    chosen = settings_for_folder(settings, "E:/Jazz")
    assert chosen.destination_root == "E:/Jazz"
    assert chosen.format == "ogg"
    assert settings.destination_root == "D:/Recordings"  # not changed in place


def test_empty_is_always_fine() -> None:
    assert folder_problem("") is None


def test_a_missing_folder_is_created(tmp_path: Path) -> None:
    target = tmp_path / "Shows" / "Jazz"
    assert folder_problem(str(target)) is None
    assert target.is_dir()


def test_a_relative_path_is_refused() -> None:
    problem = folder_problem("Jazz")
    assert problem is not None and "full path" in problem


def test_a_file_is_not_a_folder(tmp_path: Path) -> None:
    afile = tmp_path / "notes.txt"
    afile.write_text("x", encoding="utf-8")
    problem = folder_problem(str(afile))
    assert problem is not None and "is a file, not a folder" in problem


def test_a_folder_that_cannot_be_written_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _denied(*_args: object, **_kwargs: object) -> object:
        raise PermissionError("denied")

    monkeypatch.setattr(schedule_folder.tempfile, "TemporaryFile", _denied)
    problem = folder_problem(str(tmp_path))
    assert problem is not None
    assert problem.startswith(f"Recordings cannot be saved in {tmp_path}.")
    assert "cannot be written to" in problem


# -- a scheduled recording lands in its folder ------------------------------ #


class _FakeProcess:
    """Stands in for ffmpeg: alive until asked to stop."""

    def __init__(self) -> None:
        self._alive = threading.Event()
        self._alive.set()
        self.stdin = self
        self.stderr = None
        self.returncode = 0

    def write(self, data: bytes) -> None:
        if data == b"q":
            self._alive.clear()

    def flush(self) -> None:
        pass

    def poll(self) -> int | None:
        return None if self._alive.is_set() else 0

    def wait(self, timeout: float | None = None) -> int:
        deadline = time.monotonic() + (timeout or 5.0)
        while self._alive.is_set() and time.monotonic() < deadline:
            time.sleep(0.01)
        return 0

    def terminate(self) -> None:
        self._alive.clear()

    def kill(self) -> None:
        self._alive.clear()


def _fire_and_find(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: RecordingScheduleEntry
) -> Path:
    monkeypatch.setattr(recording, "find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(recording.subprocess, "Popen", lambda *a, **k: _FakeProcess())
    started: list[Path] = []
    recorder = RadioRecorder(
        on_state_changed=lambda rec, dest, _job: started.append(dest) if rec and dest else None
    )
    scheduler = RecordingScheduler(
        data_dir=tmp_path / "data",
        recorder=recorder,
        recording_settings=RecordingSettings(destination_root=str(tmp_path / "Default")),
    )
    try:
        scheduler.add(entry)
        scheduler._fire(entry, datetime(2026, 7, 14, 8, 0, 0))
        assert started, "the scheduled recording did not start"
        return started[0]
    finally:
        recorder.stop_all()
        scheduler.shutdown()


def test_a_scheduled_recording_lands_in_its_own_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    jazz = tmp_path / "Jazz"
    dest = _fire_and_find(tmp_path, monkeypatch, _entry(folder=str(jazz)))
    assert dest.parent == jazz


def test_without_a_folder_it_lands_in_the_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = _fire_and_find(tmp_path, monkeypatch, _entry())
    assert dest.parent == tmp_path / "Default"


def test_the_recordings_shelf_lists_a_schedules_own_folder(tmp_path: Path) -> None:
    from quill.core.radio.recordings_index import STATUS_RECORDED, list_recordings

    jazz = tmp_path / "Jazz"
    jazz.mkdir()
    (jazz / "WXYZ 2026-07-14.mp3").write_bytes(b"x")
    rows = list_recordings(
        RecordingSettings(destination_root=str(tmp_path / "Default")),
        scheduled=[_entry(folder=str(jazz))],
    )
    assert [r.name for r in rows if r.status == STATUS_RECORDED] == ["WXYZ 2026-07-14"]
