"""Splitting a recording at each song change (xradio2 4.8).

Everything here runs on fakes: a fake ffmpeg runner that writes the files the
segment muxer would, a fake title reader and a fake clock. No network, no
ffmpeg, no real time.
"""

from __future__ import annotations

import io
import subprocess
import threading
import time
from collections.abc import Sequence
from pathlib import Path

import pytest

from quill.core.radio import recording, recording_split
from quill.core.radio.recording import RadioRecorder, RecordingSettings
from quill.core.radio.recording_preroll_guard import OpeningGuard
from quill.core.radio.recording_song_watch import SongSplitter, SongTimeline
from quill.core.radio.recording_split import (
    MIN_SONG_SECONDS,
    SongChange,
    SplitOutcome,
    SplitPlan,
    build_segment_command,
    describe_split,
    plan_split,
    song_file_name,
    split_recording,
)

# -- names -------------------------------------------------------------------


def test_a_song_is_named_artist_then_title() -> None:
    assert song_file_name("Elton John - Your Song") == "Elton John - Your Song"


def test_characters_no_file_name_may_hold_are_removed() -> None:
    assert song_file_name('AC/DC - Back: In "Black"?') == "AC DC - Back In Black"


def test_a_structured_title_uses_its_artist_and_title_fields() -> None:
    raw = 'title="Clair de Lune",artist="Debussy",duration="300"'
    assert song_file_name(raw) == "Debussy - Clair de Lune"


@pytest.mark.parametrize("raw", ["", "   ", "???", "CON", "nul..."])
def test_a_title_with_nothing_usable_is_an_untitled_song(raw: str) -> None:
    assert song_file_name(raw) == "Untitled song"


def test_a_very_long_title_is_shortened_without_a_trailing_dot() -> None:
    name = song_file_name("A" * 79 + ". and more words after it")
    assert len(name) <= 80
    assert not name.endswith((".", " "))


# -- the plan ------------------------------------------------------------------


def _source(tmp_path: Path, name: str = "WXYZ 2026-10-17.mp3", size: int = 10_000) -> Path:
    path = tmp_path / name
    path.write_bytes(b"\xff" * size)
    return path


def test_the_plan_cuts_at_each_change_and_numbers_the_songs(tmp_path: Path) -> None:
    source = _source(tmp_path)
    plan = plan_split(
        source,
        [SongChange(100.0, "B - Two"), SongChange(300.0, "C - Three")],
        duration=500.0,
        first_title="A - One",
    )
    assert plan.splittable
    assert plan.cuts == (100.0, 300.0)
    assert plan.names == (
        "WXYZ 2026-10-17 - 01 A - One.mp3",
        "WXYZ 2026-10-17 - 02 B - Two.mp3",
        "WXYZ 2026-10-17 - 03 C - Three.mp3",
    )


def test_the_pre_roll_trim_moves_every_cut_back(tmp_path: Path) -> None:
    plan = plan_split(
        _source(tmp_path), [SongChange(100.0, "B")], duration=500.0, first_title="A", lead_trim=12.0
    )
    assert plan.cuts == (88.0,)


def test_a_flicker_shorter_than_a_song_is_folded_in(tmp_path: Path) -> None:
    flicker = MIN_SONG_SECONDS / 2
    plan = plan_split(
        _source(tmp_path),
        [SongChange(100.0, "Advert"), SongChange(100.0 + flicker, "B")],
        duration=500.0,
        first_title="A",
    )
    assert plan.cuts == (100.0,)
    assert plan.names[1].endswith("02 B.mp3")


def test_a_change_just_before_the_end_is_not_a_song(tmp_path: Path) -> None:
    plan = plan_split(
        _source(tmp_path),
        [SongChange(100.0, "B"), SongChange(495.0, "C")],
        duration=500.0,
        first_title="A",
    )
    assert plan.cuts == (100.0,)


def test_a_change_back_to_the_same_title_is_no_change(tmp_path: Path) -> None:
    plan = plan_split(_source(tmp_path), [SongChange(100.0, "A")], duration=500.0, first_title="A")
    assert not plan.splittable
    assert plan.reason == "no song change was heard while it recorded"


def test_an_unsupported_container_is_kept_whole(tmp_path: Path) -> None:
    plan = plan_split(_source(tmp_path, "show.xyz"), [SongChange(100.0, "B")], duration=500.0)
    assert not plan.splittable
    assert "cannot be split safely" in plan.reason


def test_a_missing_recording_is_kept_whole(tmp_path: Path) -> None:
    plan = plan_split(tmp_path / "gone.mp3", [SongChange(100.0, "B")], duration=500.0)
    assert not plan.splittable
    assert plan.reason == "the recording could not be found"


def test_the_segment_command_is_a_lossless_audio_only_copy(tmp_path: Path) -> None:
    args = build_segment_command(
        "ffmpeg", tmp_path / "in.mp3", [88.0, 290.5], tmp_path / "song%03d.mp3", muxer="mp3"
    )
    joined = " ".join(args)
    assert "-c copy" in joined
    assert "-map 0:a" in joined
    assert "-f segment" in joined
    assert "-segment_times 88.000,290.500" in joined
    assert "-reset_timestamps 1" in joined


# -- carrying it out ------------------------------------------------------------


class _FakeFfmpeg:
    """Writes *count* song files into the pattern's folder, sharing out the
    source's bytes, the way the segment muxer would."""

    def __init__(self, *, count: int | None = None, returncode: int = 0, size: int = 0) -> None:
        self.count = count
        self.returncode = returncode
        self.size = size
        self.calls: list[list[str]] = []

    def __call__(
        self, args: Sequence[str], *, timeout_seconds: float = 0.0
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(args))
        source = Path(args[args.index("-i") + 1])
        pattern = Path(args[-1])
        cuts = args[args.index("-segment_times") + 1].split(",")
        count = self.count if self.count is not None else len(cuts) + 1
        share = self.size or max(1, source.stat().st_size // max(1, count))
        for index in range(count):
            target = pattern.parent / (pattern.name.replace("%03d", f"{index:03d}"))
            target.write_bytes(b"\xff" * share)
        return subprocess.CompletedProcess(list(args), self.returncode, "", "boom")


def _plan(tmp_path: Path) -> SplitPlan:
    return plan_split(
        _source(tmp_path),
        [SongChange(100.0, "B - Two"), SongChange(300.0, "C - Three")],
        duration=500.0,
        first_title="A - One",
    )


def _leftovers(tmp_path: Path) -> list[str]:
    return sorted(path.name for path in tmp_path.iterdir())


def test_a_good_split_leaves_only_the_songs(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    outcome = split_recording(plan, ffmpeg="ffmpeg", runner=_FakeFfmpeg())
    assert outcome.split
    assert [path.name for path in outcome.files] == list(plan.names)
    # The whole recording is gone, the work folder too; only the songs remain.
    assert _leftovers(tmp_path) == sorted(plan.names)


def test_a_song_name_already_taken_gets_a_number(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    (tmp_path / plan.names[0]).write_bytes(b"older")
    outcome = split_recording(plan, ffmpeg="ffmpeg", runner=_FakeFfmpeg())
    assert outcome.split
    assert outcome.files[0].name == "WXYZ 2026-10-17 - 01 A - One (2).mp3"
    assert (tmp_path / plan.names[0]).read_bytes() == b"older"


@pytest.mark.parametrize(
    ("fake", "reason"),
    [
        (_FakeFfmpeg(returncode=1), "FFmpeg reported an error splitting it"),
        (_FakeFfmpeg(count=2), "FFmpeg made 2 files where 3 songs were expected"),
        (_FakeFfmpeg(size=10), "the song files were much smaller than the recording"),
    ],
)
def test_a_failed_split_keeps_the_recording_exactly_as_it_was(
    tmp_path: Path, fake: _FakeFfmpeg, reason: str
) -> None:
    plan = _plan(tmp_path)
    before = plan.source.read_bytes()
    outcome = split_recording(plan, ffmpeg="ffmpeg", runner=fake)
    assert not outcome.split
    assert outcome.reason == reason
    assert plan.source.read_bytes() == before
    assert _leftovers(tmp_path) == [plan.source.name]


def test_no_ffmpeg_keeps_the_recording(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(recording_split, "find_ffmpeg", lambda: "")
    outcome = split_recording(_plan(tmp_path), runner=_FakeFfmpeg())
    assert not outcome.split
    assert outcome.reason == "FFmpeg is not available to split it"


def test_a_song_that_cannot_be_moved_undoes_the_others(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan(tmp_path)
    real_replace = recording_split.os.replace
    moves: list[str] = []

    def _replace(src: Path, dst: Path) -> None:
        moves.append(Path(dst).name)
        if len(moves) == 2:
            raise OSError("disk said no")
        real_replace(src, dst)

    monkeypatch.setattr(recording_split.os, "replace", _replace)
    outcome = split_recording(plan, ffmpeg="ffmpeg", runner=_FakeFfmpeg())
    assert not outcome.split
    assert outcome.reason == "the song files could not be saved"
    assert _leftovers(tmp_path) == [plan.source.name]


def test_what_is_said_carries_the_count_or_the_reason(tmp_path: Path) -> None:
    source = tmp_path / "show.mp3"
    songs = (tmp_path / "show - 01 A.mp3", tmp_path / "show - 02 B.mp3")
    assert describe_split(SplitOutcome(True, source, songs)) == (
        "Split show.mp3 into 2 songs, starting with show - 01 A.mp3."
    )
    assert describe_split(SplitOutcome(False, source, (source,), "no song change was heard")) == (
        "Kept show.mp3 as one recording: no song change was heard."
    )


# -- hearing the changes ---------------------------------------------------------


def test_the_timeline_puts_a_change_between_the_two_polls() -> None:
    timeline = SongTimeline(station_name="WXYZ", started=1000.0)
    assert not timeline.hear("A - One", 1000.0)
    assert not timeline.hear("A - One", 1010.0)
    assert timeline.hear("B - Two", 1020.0)
    assert timeline.first_title == "A - One"
    assert timeline.changes == [SongChange(15.0, "B - Two")]


@pytest.mark.parametrize("noise", ["", "Live", "WXYZ", "Advertisement"])
def test_the_station_talking_about_itself_is_not_a_song(noise: str) -> None:
    timeline = SongTimeline(station_name="WXYZ", started=0.0)
    timeline.hear("A - One", 0.0)
    assert not timeline.hear(noise, 10.0)
    assert timeline.changes == []


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _splitter(titles: list[str], clock: _Clock, plans: list[SplitPlan]) -> SongSplitter:
    def read(_url: str) -> str:
        return titles.pop(0) if titles else ""

    def split(plan: SplitPlan) -> SplitOutcome:
        plans.append(plan)
        return SplitOutcome(True, plan.source, tuple(plan.source.with_name(n) for n in plan.names))

    return SongSplitter(read_title=read, clock=clock, split=split, start_threads=False)


def test_the_splitter_cuts_at_what_it_heard(tmp_path: Path) -> None:
    clock = _Clock()
    plans: list[SplitPlan] = []
    splitter = _splitter(["A - One", "B - Two"], clock, plans)
    splitter.connection("job", "http://x.test/live", enabled=True, continuation=False)
    clock.now = 10.0
    splitter.poll_now("job")
    clock.now = 130.0
    splitter.poll_now("job")
    clock.now = 400.0
    said = splitter.finish("job", _source(tmp_path))
    assert plans[0].cuts == (70.0,)
    assert said.startswith("Split WXYZ 2026-10-17.mp3 into 2 songs")
    assert not splitter.watching("job")


def test_the_setting_off_means_no_watch_and_nothing_said(tmp_path: Path) -> None:
    splitter = _splitter([], _Clock(), [])
    splitter.connection("job", "http://x.test/live", enabled=False, continuation=False)
    assert not splitter.watching("job")
    assert splitter.finish("job", _source(tmp_path)) == ""


def test_a_recording_that_dropped_is_kept_whole_and_says_why(tmp_path: Path) -> None:
    plans: list[SplitPlan] = []
    splitter = _splitter(["A", "B"], _Clock(), plans)
    splitter.connection("job", "http://x.test/live", enabled=True, continuation=False)
    splitter.connection("job", "http://x.test/live", enabled=True, continuation=True)
    said = splitter.finish("job", _source(tmp_path))
    assert plans == []
    assert "the stream dropped while it recorded" in said


def test_parts_that_could_not_be_joined_are_not_split(tmp_path: Path) -> None:
    splitter = _splitter([], _Clock(), [])
    splitter.connection("job", "http://x.test/live", enabled=True, continuation=False)
    assert "could not be joined" in splitter.finish("job", None)


def test_the_setting_round_trips_and_defaults_off() -> None:
    assert RecordingSettings().split_at_song_changes is False
    on = RecordingSettings(split_at_song_changes=True)
    assert RecordingSettings.from_dict(on.to_dict()).split_at_song_changes is True
    assert RecordingSettings.from_dict({}).split_at_song_changes is False


# -- through the recorder ------------------------------------------------------


def _quiet_guard() -> OpeningGuard:
    """A pre-roll guard that hears nothing and waits for nothing."""
    return OpeningGuard(
        decode=lambda _source: None,
        trim=lambda _path, _seconds: False,
        delay_seconds=0.0,
        wait_seconds=0.5,
    )


class _Stdin:
    def __init__(self, process: _Process) -> None:
        self._process = process

    def write(self, data: bytes) -> None:
        if data == b"q":
            self._process.alive.clear()

    def flush(self) -> None:
        pass


class _Process:
    """A fake ffmpeg that writes some audio and runs until asked to quit."""

    def __init__(self, out_path: Path) -> None:
        out_path.write_bytes(b"\xff" * 20_000)
        self.alive = threading.Event()
        self.alive.set()
        self.returncode = 0
        self.stdin = _Stdin(self)
        self.stderr = io.BytesIO(b"")

    def poll(self) -> int | None:
        return None if self.alive.is_set() else 0

    def wait(self, timeout: float | None = None) -> int:
        deadline = time.monotonic() + (timeout if timeout is not None else 30.0)
        while self.alive.is_set() and time.monotonic() < deadline:
            time.sleep(0.01)
        if self.alive.is_set():
            raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=timeout or 0)
        return 0

    def terminate(self) -> None:
        self.alive.clear()


def test_the_recorder_splits_a_finished_recording_and_says_so(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(recording, "find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(recording.subprocess, "Popen", lambda args, **_kw: _Process(Path(args[-1])))
    clock = _Clock()
    plans: list[SplitPlan] = []
    notes: list[str] = []
    recorder = RadioRecorder(on_parts_joined=notes.append)
    recorder._openings = _quiet_guard()
    recorder._songs = _splitter(["A - One", "B - Two"], clock, plans)
    recorder.start(
        station_name="WXYZ",
        stream_url="http://example.test/live",
        settings=RecordingSettings(destination_root=str(tmp_path), split_at_song_changes=True),
        duration_minutes=60,
    )
    job_id = recorder.active_jobs()[0].job_id
    assert recorder._songs.watching(job_id)
    clock.now = 5.0
    recorder._songs.poll_now(job_id)
    clock.now = 95.0
    recorder._songs.poll_now(job_id)
    clock.now = 300.0
    recorder.stop()
    deadline = time.monotonic() + 10
    while not notes and time.monotonic() < deadline:
        time.sleep(0.02)
    assert plans and plans[0].cuts == (50.0,)
    assert notes and notes[-1].startswith("Split ")
    assert "into 2 songs" in notes[-1]


def test_the_recorder_says_nothing_extra_with_the_setting_off(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(recording, "find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(recording.subprocess, "Popen", lambda args, **_kw: _Process(Path(args[-1])))
    ended = threading.Event()
    notes: list[str] = []
    recorder = RadioRecorder(
        on_parts_joined=notes.append,
        on_state_changed=lambda active, _dest, _job: None if active else ended.set(),
    )
    recorder._openings = _quiet_guard()
    recorder.start(
        station_name="WXYZ",
        stream_url="http://example.test/live",
        settings=RecordingSettings(destination_root=str(tmp_path)),
        duration_minutes=60,
    )
    job_id = recorder.active_jobs()[0].job_id
    assert not recorder._songs.watching(job_id)
    recorder.stop()
    assert ended.wait(10)
    time.sleep(0.2)
    assert notes == []
