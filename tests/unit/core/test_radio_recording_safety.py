"""Recording preservation and Stop through hand-offs (plan.md, "Windows Radio
recording and recovery review", 2026-11-20).

Each test reproduces one reviewed failure against the real code path, with a
fake ffmpeg, fake clocks and gates -- no audio, network or ffmpeg is used:

1. startup recovery replaced a kept recording with a same-name orphan;
2. Stop All missed a reconnect that was handing off to its continuation;
3. recovery looked for ``.copy`` files, stranding raw ``.aac`` captures;
4. a continuation took the recorder past the user's concurrency cap;
5. a time-zone/DST shift stretched the reconnect's remaining time;
6. the Recordings summary raised ``TypeError`` for an enabled daily schedule;
7. a continued capture said "less than a minute left" with ten to go;
8. a schedule deleted during a slow start still recorded.
"""

from __future__ import annotations

import errno
import os
import shutil
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import quill.core.radio.recording as recording
import quill.core.radio.recording_job as recording_job
import quill.core.radio.recording_outcome as recording_outcome
from quill.core.radio import recording_center
from quill.core.radio.recording import (
    RadioRecorder,
    RecordingLimitError,
    RecordingSettings,
)
from quill.core.radio.recording_outcome import finalize_move
from quill.core.radio.recording_progress import RecordingProgress, recording_cell_text
from quill.core.radio.recording_resume import ActiveRecordingMarker, reconcile_temp_strays
from quill.core.radio.recording_schedule import RecordingScheduleEntry, RecordingScheduler
from quill.core.radio.recordings_index import STATUS_RECORDING, RecordingEntry

_AUDIO = 20_000  # comfortably above MIN_USEFUL_CAPTURE_BYTES


def _age(path: Path, seconds: float = 3600) -> None:
    old = time.time() - seconds
    os.utime(path, (old, old))


# -- 1 and 3: crash recovery keeps everything --------------------------------


def test_finalize_move_keeps_an_existing_recording_byte_for_byte(tmp_path: Path) -> None:
    temp = tmp_path / "temp"
    home = tmp_path / "home"
    temp.mkdir()
    home.mkdir()
    kept = home / "Show.mp3"
    kept.write_bytes(b"kept" * 5000)
    orphan = temp / "Show.mp3"
    orphan.write_bytes(b"orphan" * 5000)

    landed = finalize_move(orphan, kept)

    assert landed == home / "Show (2).mp3"
    assert kept.read_bytes() == b"kept" * 5000
    assert landed.read_bytes() == b"orphan" * 5000
    assert not orphan.exists()


def test_startup_recovery_never_replaces_a_same_name_recording(tmp_path: Path) -> None:
    temp = tmp_path / "temp"
    home = tmp_path / "home"
    temp.mkdir()
    home.mkdir()
    kept = home / "KFI - 2026-11-19 20-00-00.mp3"
    kept.write_bytes(b"A" * _AUDIO)
    orphan = temp / kept.name
    orphan.write_bytes(b"B" * _AUDIO)
    _age(orphan)

    moved = reconcile_temp_strays(SimpleNamespace(temp_dir=str(temp), destination_root=str(home)))

    assert moved == [home / "KFI - 2026-11-19 20-00-00 (2).mp3"]
    assert kept.read_bytes() == b"A" * _AUDIO
    assert moved[0].read_bytes() == b"B" * _AUDIO
    assert list(temp.iterdir()) == []


def test_cross_volume_recovery_copies_beside_the_existing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _no_link(_src: object, _dst: object) -> None:
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    monkeypatch.setattr(recording_outcome.os, "link", _no_link)
    kept = tmp_path / "home" / "Show.aac"
    kept.parent.mkdir()
    kept.write_bytes(b"A" * _AUDIO)
    orphan = tmp_path / "Show.aac"
    orphan.write_bytes(b"B" * _AUDIO)

    landed = finalize_move(orphan, kept)

    assert landed == kept.parent / "Show (2).aac"
    assert kept.read_bytes() == b"A" * _AUDIO
    assert landed.read_bytes() == b"B" * _AUDIO
    assert not orphan.exists()


def test_a_failed_cross_volume_copy_leaves_both_files_and_no_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _no_link(_src: object, _dst: object) -> None:
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    def _dies_half_way(reader: Any, writer: Any, *_a: object) -> None:
        writer.write(reader.read(100))
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(recording_outcome.os, "link", _no_link)
    monkeypatch.setattr(recording_outcome.shutil, "copyfileobj", _dies_half_way)
    kept = tmp_path / "home" / "Show.mp3"
    kept.parent.mkdir()
    kept.write_bytes(b"A" * _AUDIO)
    orphan = tmp_path / "Show.mp3"
    orphan.write_bytes(b"B" * _AUDIO)

    landed = finalize_move(orphan, kept)

    assert landed == orphan  # left in temp, still playable
    assert orphan.read_bytes() == b"B" * _AUDIO
    assert kept.read_bytes() == b"A" * _AUDIO
    assert sorted(p.name for p in kept.parent.iterdir()) == ["Show.mp3"]


def test_a_name_taken_during_the_move_is_not_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_link = os.link
    raced: list[Path] = []

    def _racing_link(src: Any, dst: Any) -> None:
        if not raced:
            raced.append(Path(dst))
            Path(dst).write_bytes(b"late arrival")
        real_link(src, dst)

    monkeypatch.setattr(recording_outcome.os, "link", _racing_link)
    orphan = tmp_path / "temp.mp3"
    orphan.write_bytes(b"B" * _AUDIO)
    target = tmp_path / "home" / "Show.mp3"

    landed = finalize_move(orphan, target)

    assert raced == [target]
    assert target.read_bytes() == b"late arrival"
    assert landed == target.parent / "Show (2).mp3"
    assert landed.read_bytes() == b"B" * _AUDIO


@pytest.mark.parametrize("suffix", [".aac", ".mka", ".opus", ".m4a", ".ac3", ".mp3"])
def test_recovery_finds_every_actual_recording_extension(tmp_path: Path, suffix: str) -> None:
    temp = tmp_path / "temp"
    home = tmp_path / "home"
    temp.mkdir()
    orphan = temp / f"Raw capture{suffix}"
    orphan.write_bytes(b"R" * _AUDIO)
    _age(orphan)
    unrelated = temp / "notes.txt"
    unrelated.write_text("not a recording")
    _age(unrelated)

    moved = reconcile_temp_strays(SimpleNamespace(temp_dir=str(temp), destination_root=str(home)))

    assert moved == [home / orphan.name]
    assert moved[0].read_bytes() == b"R" * _AUDIO
    assert unrelated.exists()


def test_recovery_sends_an_orphan_to_the_folder_its_marker_recorded(tmp_path: Path) -> None:
    temp = tmp_path / "temp"
    default_home = tmp_path / "home"
    schedule_home = tmp_path / "Morning show"
    temp.mkdir()
    orphan = temp / "Morning.mp3"
    orphan.write_bytes(b"M" * _AUDIO)
    _age(orphan)
    marker = ActiveRecordingMarker(
        station_name="KFI",
        stream_url="https://example.test/kfi",
        temp_path=str(orphan),
        output_path=str(schedule_home / "Morning.mp3"),
        started_at="2026-11-19T06:00:00",
        scheduled_end="2026-11-19T07:00:00",
        duration_minutes=60,
        job_id="job",
    )

    moved = reconcile_temp_strays(
        SimpleNamespace(temp_dir=str(temp), destination_root=str(default_home)),
        markers=[marker],
    )

    assert moved == [schedule_home / "Morning.mp3"]
    assert not default_home.exists()


def test_a_file_recovery_cannot_move_is_not_announced_as_recovered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    temp = tmp_path / "temp"
    temp.mkdir()
    orphan = temp / "Show.mp3"
    orphan.write_bytes(b"B" * _AUDIO)
    _age(orphan)

    def _fails(_src: object, _dst: object) -> None:
        raise PermissionError(errno.EACCES, "denied")

    monkeypatch.setattr(recording_outcome, "_move_no_clobber", _fails)
    moved = reconcile_temp_strays(
        SimpleNamespace(temp_dir=str(temp), destination_root=str(tmp_path / "home"))
    )
    assert moved == []
    assert orphan.read_bytes() == b"B" * _AUDIO


# -- a recorder rig: fake ffmpeg, fake clocks, gates ---------------------------


class _Stdin:
    def __init__(self, process: _Ffmpeg) -> None:
        self._process = process

    def write(self, data: bytes) -> None:
        if data == b"q":
            self._process.exit(0)

    def flush(self) -> None:
        pass


class _Ffmpeg:
    """A fake ffmpeg that writes some audio and runs until stopped or dropped."""

    def __init__(self, args: list[str]) -> None:
        self.args = args
        Path(args[-1]).write_bytes(b"\xff" * _AUDIO)
        self._alive = threading.Event()
        self._alive.set()
        self.returncode: int | None = None
        self.stdin = _Stdin(self)
        self.stderr = None
        self.terminated = False

    @property
    def seconds(self) -> int:
        return int(self.args[self.args.index("-t") + 1])

    def exit(self, code: int) -> None:
        self.returncode = code
        self._alive.clear()

    def drop(self) -> None:
        """The stream went away: a non-zero, non-fatal exit."""
        self.exit(1)

    def poll(self) -> int | None:
        return None if self._alive.is_set() else self.returncode

    def wait(self, timeout: float | None = None) -> int:
        if not self._alive.wait(0) and self.returncode is not None:
            return self.returncode
        deadline = time.monotonic() + (timeout if timeout is not None else 30.0)
        while self._alive.is_set() and time.monotonic() < deadline:
            time.sleep(0.005)
        if self._alive.is_set():
            raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=timeout or 0)
        return self.returncode or 0

    def terminate(self) -> None:
        self.terminated = True
        self.exit(-15)

    kill = terminate


class _Inert:
    """Stands in for the pre-roll guard and song splitter: nothing to decode."""

    def begin(self, *_a: object, **_k: object) -> None:
        pass

    def connection(self, *_a: object, **_k: object) -> None:
        pass

    def discard(self, *_a: object) -> None:
        pass

    def cancel_all(self) -> None:
        pass

    def strip(self, _job: str, parts: list[Path]) -> tuple[list[Path], str]:
        return parts, ""

    def take_lead_trim(self, _job: str) -> float:
        return 0.0

    def finish(self, *_a: object, **_k: object) -> str:
        return ""


class _Gate:
    """Holds a thread at one step of a start until the test releases it."""

    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.armed = False

    def __call__(self) -> None:
        if not self.armed:
            return
        self.armed = False
        self.entered.set()
        assert self.release.wait(10), "gate never released"


class _Clock:
    """Monotonic seconds, UTC and the listener's wall clock, moved by the test."""

    def __init__(self) -> None:
        self.mono = 1000.0
        self.utc = datetime(2026, 11, 1, 6, 0, tzinfo=UTC)
        self.local = datetime(2026, 11, 1, 1, 0)

    def advance(self, minutes: float, *, wall_shift_hours: float = 0.0) -> None:
        self.mono += minutes * 60
        self.utc += timedelta(minutes=minutes)
        self.local += timedelta(minutes=minutes, hours=wall_shift_hours)


@pytest.fixture
def rig(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[SimpleNamespace]:
    before = set(threading.enumerate())
    launched: list[_Ffmpeg] = []
    gates = {name: _Gate() for name in ("resolve", "probe", "spawn", "register", "wait")}
    clock = _Clock()

    def _popen(args: list[str], **_kw: object) -> _Ffmpeg:
        gates["spawn"]()
        process = _Ffmpeg(args)
        launched.append(process)
        return process

    def _resolve(url: str) -> str:
        gates["resolve"]()
        return url

    def _probe(_url: str) -> str:
        gates["probe"]()
        return "aac"

    def _job_object(_process: object) -> None:
        gates["register"]()
        return None

    monkeypatch.setattr(recording, "find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(recording.subprocess, "Popen", _popen)
    monkeypatch.setattr(recording, "_resolve_capture_url", _resolve)
    monkeypatch.setattr(recording, "probe_capture_extension", _probe)
    monkeypatch.setattr(recording, "assign_kill_on_close_job", _job_object)
    monkeypatch.setattr(recording_job, "reconnect_wait", lambda _s: gates["wait"]())
    monkeypatch.setattr(
        recording,
        "join_recording_parts",
        lambda parts: SimpleNamespace(joined=False, path=parts[0]),
    )
    monkeypatch.setattr(recording, "describe_join", lambda _outcome: "")
    monkeypatch.setattr(recording_job, "monotonic", lambda: clock.mono)
    monkeypatch.setattr(recording_job, "utc_now", lambda: clock.utc)
    monkeypatch.setattr(recording, "local_now", lambda: clock.local)
    reports: list[Any] = []
    reconnects: list[int] = []

    def _recorder() -> RadioRecorder:
        made = RadioRecorder(
            on_finished=reports.append,
            on_reconnect=lambda attempt, _max: reconnects.append(attempt),
        )
        made._openings = _Inert()  # type: ignore[assignment]
        made._songs = _Inert()  # type: ignore[assignment]
        return made

    def settings(**overrides: Any) -> RecordingSettings:
        base: dict[str, Any] = {
            "destination_root": str(tmp_path / "home"),
            "reconnect_wait_seconds": 1,
            "reconnect_max_attempts": 3,
        }
        base.update(overrides)
        return RecordingSettings(**base)

    made: list[RadioRecorder] = []

    def recorder() -> RadioRecorder:
        made.append(_recorder())
        return made[-1]

    yield SimpleNamespace(
        launched=launched,
        gates=gates,
        clock=clock,
        recorder=recorder,
        settings=settings,
        reports=reports,
        reconnects=reconnects,
    )
    for gate in gates.values():
        gate.armed = False
        gate.release.set()
    for each in made:
        each.shutdown()
    # Every monitor thread must finish while the fakes are still patched in:
    # one outliving the test would join its parts with whatever ``Popen`` the
    # next test (or nobody) has installed.
    assert _until(
        lambda: (
            not any(
                t.name == "quill-radio-record-monitor" and t.is_alive() and t not in before
                for t in threading.enumerate()
            )
        ),
        10.0,
    ), "a recorder monitor thread outlived its test"


def _data(tmp_path: Path) -> Path:
    folder = tmp_path / "data"
    folder.mkdir(exist_ok=True)
    return folder


def _until(condition: Callable[[], bool], seconds: float = 5.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.005)
    return condition()


def _live(launched: list[_Ffmpeg]) -> list[_Ffmpeg]:
    return [p for p in launched if p.poll() is None]


# -- 2: Stop All reaches a reconnect at every step of its hand-off -------------


@pytest.mark.parametrize("step", ["wait", "resolve", "probe", "spawn", "register"])
def test_stop_all_cancels_a_reconnect_at_every_step_of_the_hand_off(
    rig: SimpleNamespace, step: str
) -> None:
    recorder = rig.recorder()
    raw = step == "probe"  # the codec probe only runs for a raw capture
    recorder.start(
        station_name="KFI",
        stream_url="https://example.test/kfi",
        settings=rig.settings(format="copy" if raw else "mp3"),
        duration_minutes=60,
    )
    if raw:
        # A continuation reuses the probed extension; force a fresh probe so
        # the gate is on the hand-off path.
        recorder._jobs[next(iter(recorder._jobs))].extension = ""
    gate = rig.gates[step]
    gate.armed = True
    rig.launched[0].drop()
    assert gate.entered.wait(5), f"the reconnect never reached {step}"

    # The recording is mid-hand-off: neither running nor gone. Stop All must
    # be able to see it, and must stop it.
    assert recorder.active_count + recorder.waiting_count == 1
    recorder.stop_all()
    gate.release.set()

    assert _until(lambda: len(rig.reports) == 1)
    assert _live(rig.launched) == []
    assert recorder.active_count == 0
    assert recorder.waiting_count == 0
    assert rig.reports[0].how == "stopped"
    for process in rig.launched[1:]:
        assert process.terminated, "a continuation spawned after Stop must be killed"


def test_shutdown_during_spawn_kills_the_continuation(rig: SimpleNamespace) -> None:
    recorder = rig.recorder()
    recorder.start(
        station_name="KFI",
        stream_url="https://example.test/kfi",
        settings=rig.settings(),
        duration_minutes=60,
    )
    rig.gates["register"].armed = True
    rig.launched[0].drop()
    assert rig.gates["register"].entered.wait(5)
    recorder.shutdown()
    rig.gates["register"].release.set()
    assert _until(lambda: len(rig.reports) == 1)
    assert _live(rig.launched) == []


# -- 4: a reconnecting recording owns its concurrency slot ---------------------


def test_a_reconnecting_recording_keeps_its_slot_under_the_cap(rig: SimpleNamespace) -> None:
    recorder = rig.recorder()
    capped = rig.settings(max_concurrent_recordings=1)
    recorder.start(
        station_name="A",
        stream_url="https://example.test/a",
        settings=capped,
        duration_minutes=60,
    )
    rig.gates["wait"].armed = True
    rig.launched[0].drop()
    assert rig.gates["wait"].entered.wait(5)

    with pytest.raises(RecordingLimitError):
        recorder.start(
            station_name="B",
            stream_url="https://example.test/b",
            settings=capped,
            duration_minutes=60,
        )
    rig.gates["wait"].release.set()

    assert _until(lambda: len(rig.launched) == 2 and recorder.active_count == 1)
    assert recorder.active_count == 1
    assert [p.args[-1] for p in _live(rig.launched)] == [rig.launched[1].args[-1]]
    assert "(part 2)" in rig.launched[1].args[-1]


def test_a_scheduled_show_is_held_not_dropped_while_a_slot_is_reconnecting(
    rig: SimpleNamespace, tmp_path: Path
) -> None:
    recorder = rig.recorder()
    capped = rig.settings(max_concurrent_recordings=1)
    recorder.start(
        station_name="A",
        stream_url="https://example.test/a",
        settings=capped,
        duration_minutes=60,
    )
    rig.gates["wait"].armed = True
    rig.launched[0].drop()
    assert rig.gates["wait"].entered.wait(5)

    busy: list[str] = []
    fired: list[tuple[str, str]] = []
    scheduler = RecordingScheduler(
        data_dir=_data(tmp_path),
        recorder=recorder,
        recording_settings=capped,
        on_busy=lambda entry: busy.append(entry.id),
        on_fired=lambda entry, error: fired.append((entry.id, error)),
    )
    try:
        now = datetime.now()
        entry = _entry(now)
        scheduler.add(entry)
        scheduler._fire(entry, now)
        assert busy == [entry.id]  # announced once, held for a retry
        assert fired == []
        assert scheduler.entries[0].last_fired_date == ""  # not burned
        assert scheduler.entries[0].enabled
    finally:
        scheduler.shutdown()


# -- 5: deadlines are elapsed time, not the mutable wall clock -----------------


@pytest.mark.parametrize(
    "wall_shift_hours",
    [0.0, 3.0, -3.0, 1.0, -1.0],
    ids=["no-shift", "zone+3h", "zone-3h", "dst-spring", "dst-fall"],
)
def test_a_reconnect_records_the_true_remaining_time_across_a_clock_shift(
    rig: SimpleNamespace, wall_shift_hours: float
) -> None:
    recorder = rig.recorder()
    recorder.start(
        station_name="KFI",
        stream_url="https://example.test/kfi",
        settings=rig.settings(),
        duration_minutes=60,
    )
    # Half-way through, the computer's time zone (or DST) changes, then the
    # stream drops.
    rig.clock.advance(30, wall_shift_hours=wall_shift_hours)
    rig.launched[0].drop()
    assert _until(lambda: len(rig.launched) == 2)

    assert rig.launched[1].seconds == 30 * 60
    # The continuation keeps the original filename timestamp (local time).
    assert "2026-11-01 01-00-00 (part 2)" in rig.launched[1].args[-1]


def test_a_drop_after_the_true_end_does_not_reconnect_despite_a_clock_rewind(
    rig: SimpleNamespace,
) -> None:
    recorder = rig.recorder()
    recorder.start(
        station_name="KFI",
        stream_url="https://example.test/kfi",
        settings=rig.settings(),
        duration_minutes=60,
    )
    rig.clock.advance(61, wall_shift_hours=-3)  # the wall clock says 58 min elapsed... minus 3h
    rig.launched[0].drop()
    assert _until(lambda: len(rig.reports) == 1)
    assert len(rig.launched) == 1
    assert rig.reconnects == []
    assert rig.reports[0].how == "finished"


# -- 6: the real Recordings summary with a real daily schedule -----------------


def _entry(now: datetime, *, minutes_ahead: int = 0, **overrides: Any) -> RecordingScheduleEntry:
    start = now + timedelta(minutes=minutes_ahead)
    base: dict[str, Any] = {
        "id": "entry-1",
        "station_name": "KFI",
        "stream_url": "https://example.test/kfi",
        "recurrence": "daily",
        "run_at": start.strftime("%Y-%m-%dT%H:%M"),
        "duration_minutes": 60,
    }
    base.update(overrides)
    return RecordingScheduleEntry(**base)


@pytest.mark.parametrize("minutes_ahead", [20, 180])
def test_the_summary_composes_with_a_real_enabled_daily_schedule(minutes_ahead: int) -> None:
    now = datetime.now().replace(second=0, microsecond=0)  # naive, as the dialog passes
    entry = _entry(now, minutes_ahead=minutes_ahead)

    line = recording_center.summary_from_rows([], [entry], folder="D:\\Recordings", now=now)

    assert line.startswith("Not recording. Next: KFI ")
    if minutes_ahead < 60:
        assert "KFI in 20 minutes" in line
    else:
        assert f"KFI at {(now + timedelta(minutes=180)).strftime('%H:%M')}" in line


def test_the_summary_composes_with_a_schedule_in_another_time_zone() -> None:
    now = datetime.now().replace(second=0, microsecond=0)
    entry = _entry(now, minutes_ahead=600, timezone="Pacific/Auckland")
    line = recording_center.summary_from_rows([], [entry], folder="", now=now)
    assert "Next: KFI" in line


# -- 7: a continued capture counts down to the real end ------------------------


def test_a_continued_capture_reports_the_true_time_left(rig: SimpleNamespace) -> None:
    rig.clock.utc = datetime.now(UTC) - timedelta(minutes=50)
    recorder = rig.recorder()
    recorder.start(
        station_name="KFI",
        stream_url="https://example.test/kfi",
        settings=rig.settings(),
        duration_minutes=60,
    )
    rig.clock.advance(50)
    rig.launched[0].drop()
    assert _until(lambda: len(rig.launched) == 2 and recorder.active_count == 1)

    (snapshot,) = recorder.active_jobs()
    assert snapshot.minutes == 60  # the show's planned length, not the part's
    assert rig.launched[1].seconds == 10 * 60  # ffmpeg is told only the rest

    # The status bar, built from the real recorder.
    from quill.ui.radio.status_bar import RadioStatusBar

    host = SimpleNamespace(_wx=None, _radio_recorder=recorder)
    assert RadioStatusBar(host)._label_record() == "Stop Recording (10 min left)"

    # The Recordings window's headline, from a row carrying the snapshot.
    row = RecordingEntry(
        id="row",
        name="KFI",
        status=STATUS_RECORDING,
        path=snapshot.destination,
        started_at=snapshot.started_at,
        job_id=snapshot.job_id,
        scheduled_minutes=snapshot.minutes,
        duration_requested=snapshot.duration_requested,
        ends_at=snapshot.ends_at,
    )
    line = recording_center.summary_from_rows([row], [], folder="", now=datetime.now())
    assert line.startswith("Recording, 10 min left.")


def test_progress_prefers_the_stable_end_over_start_plus_minutes() -> None:
    now = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
    continued = RecordingProgress(
        started_at=datetime(2026, 11, 1, 11, 10, tzinfo=UTC),
        minutes=10,  # what an old snapshot carried: the part's remaining time
        duration_requested=True,
        ends_at=datetime(2026, 11, 1, 12, 10, tzinfo=UTC),
    )
    assert recording_cell_text([continued], now) == "10 min left"


# -- 8: a deleted due schedule never starts -----------------------------------


@pytest.mark.parametrize("change", ["remove", "edit"])
def test_a_schedule_withdrawn_during_a_slow_start_does_not_record(
    rig: SimpleNamespace, tmp_path: Path, change: str
) -> None:
    recorder = rig.recorder()
    fired: list[tuple[str, str]] = []
    scheduler = RecordingScheduler(
        data_dir=_data(tmp_path),
        recorder=recorder,
        recording_settings=rig.settings(),
        on_fired=lambda entry, error: fired.append((entry.id, error)),
    )
    try:
        now = datetime.now()
        scheduler.add(_entry(now))
        snapshot = list(scheduler.entries)
        version = snapshot[0].to_dict()
        rig.gates["spawn"].armed = True
        worker = threading.Thread(
            target=scheduler._fire, args=(snapshot[0], now), kwargs={"version": version}
        )
        worker.start()
        assert rig.gates["spawn"].entered.wait(5)
        if change == "remove":
            assert scheduler.remove("entry-1") is True
        else:
            assert scheduler.update(_entry(now, station_name="KFI (edited)")) is True
        rig.gates["spawn"].release.set()
        worker.join(5)

        assert _live(rig.launched) == []
        assert recorder.active_count == 0
        assert fired == []
        if change == "remove":
            assert scheduler.entries == []
        else:
            assert scheduler.entries[0].last_fired_date == ""
    finally:
        scheduler.shutdown()


def test_a_schedule_removed_after_the_snapshot_never_reaches_ffmpeg(
    rig: SimpleNamespace, tmp_path: Path
) -> None:
    recorder = rig.recorder()
    scheduler = RecordingScheduler(
        data_dir=_data(tmp_path), recorder=recorder, recording_settings=rig.settings()
    )
    try:
        now = datetime.now()
        scheduler.add(_entry(now))
        stale = list(scheduler.entries)[0]
        version = stale.to_dict()
        scheduler.remove("entry-1")
        scheduler._fire(stale, now, version=version)
        assert rig.launched == []
    finally:
        scheduler.shutdown()


def test_an_unchanged_schedule_still_records(rig: SimpleNamespace, tmp_path: Path) -> None:
    recorder = rig.recorder()
    fired: list[tuple[str, str]] = []
    scheduler = RecordingScheduler(
        data_dir=_data(tmp_path),
        recorder=recorder,
        recording_settings=rig.settings(),
        on_fired=lambda entry, error: fired.append((entry.id, error)),
    )
    try:
        now = datetime.now()
        scheduler.add(_entry(now))
        entry = scheduler.entries[0]
        scheduler._fire(entry, now, version=entry.to_dict())
        assert recorder.active_count == 1
        assert fired == [("entry-1", "")]
    finally:
        scheduler.shutdown()


def test_shutil_is_the_module_finalize_move_copies_with() -> None:
    # The cross-volume tests patch recording_outcome.shutil; keep them honest.
    assert recording_outcome.shutil is shutil
